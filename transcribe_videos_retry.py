import os
from openai import OpenAI
from pathlib import Path
import json
from datetime import datetime
from dotenv import load_dotenv
from pydub import AudioSegment
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcription.log')
    ]
)

# Load environment variables from .env file
load_dotenv()

class TranscriptionManager:
    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.client = OpenAI()
        self.max_file_size = 25 * 1024 * 1024  # 25MB in bytes
        self.failed_files = []
        self.retry_delay = 20  # seconds between retries
        self.max_retries = 3
        self.chunk_length_ms = 10 * 60 * 1000  # 10 minutes in milliseconds

    def get_supported_extensions(self):
        """Returns a set of supported audio file extensions by OpenAI's Whisper API"""
        return {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}

    def create_output_filename(self, input_path, output_dir="Transcriptions", part=None):
        """Creates an output filename for the transcription"""
        try:
            Path(output_dir).mkdir(exist_ok=True)
            stem = Path(input_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if part is not None:
                return os.path.join(output_dir, f"{stem}_part{part}_{timestamp}.txt")
            return os.path.join(output_dir, f"{stem}_{timestamp}.txt")
        except Exception as e:
            logging.error(f"Error creating output filename: {e}")
            raise

    def get_file_size(self, file_path):
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logging.error(f"Error getting file size for {file_path}: {e}")
            raise

    def split_audio_file(self, file_path):
        """Split large audio files into chunks under 25MB"""
        chunks = []  # Initialize chunks list before try block
        try:
            logging.info(f"Splitting large file: {os.path.basename(file_path)}")
            
            # Load audio file
            audio = AudioSegment.from_file(file_path)
            
            # Split audio into chunks
            for i, chunk_start in enumerate(range(0, len(audio), self.chunk_length_ms)):
                chunk = audio[chunk_start:chunk_start + self.chunk_length_ms]
                chunk_path = f"temp_chunk_{i}.mp3"
                chunk.export(chunk_path, format="mp3", parameters=["-q:a", "1"])  # Higher quality MP3
                chunks.append(chunk_path)
            
            return chunks
            
        except Exception as e:
            logging.error(f"Error splitting audio file {file_path}: {e}")
            # Clean up any temporary files
            for chunk in chunks:  # Now chunks is guaranteed to exist
                if os.path.exists(chunk):
                    os.remove(chunk)
            raise

    def transcribe_file(self, file_path, retries=0):
        """Transcribe a single audio file using OpenAI's Whisper API"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check file size
            if self.get_file_size(file_path) > self.max_file_size:
                return self.handle_large_file(file_path)

            with open(file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
                
                output_file = self.create_output_filename(file_path)
                self.save_transcription(output_file, file_path, transcription)
                logging.info(f"✓ Successfully transcribed: {os.path.basename(file_path)}")
                logging.info(f"  Saved to: {output_file}")
                return True

        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg and retries < self.max_retries:
                logging.warning(f"Quota error for {os.path.basename(file_path)}. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                return self.transcribe_file(file_path, retries + 1)
            else:
                logging.error(f"✗ Error transcribing {os.path.basename(file_path)}: {error_msg}")
                self.failed_files.append((file_path, error_msg))
                return False

    def handle_large_file(self, file_path):
        """Handle files larger than 25MB by splitting them"""
        chunks = None  # Initialize chunks as None
        try:
            chunks = self.split_audio_file(file_path)
            all_text = []

            for i, chunk_path in enumerate(chunks):
                try:
                    with open(chunk_path, "rb") as audio_file:
                        transcription = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json"
                        )
                        all_text.append(transcription.text)
                    
                finally:
                    # Clean up chunk file
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)

            # Save combined transcription
            output_file = self.create_output_filename(file_path)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcription of: {os.path.basename(file_path)}\n")
                f.write(f"Transcribed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n\n")
                f.write("\n".join(all_text))
            
            logging.info(f"✓ Successfully transcribed large file: {os.path.basename(file_path)}")
            logging.info(f"  Saved to: {output_file}")
            return True

        except Exception as e:
            logging.error(f"Error handling large file {file_path}: {e}")
            self.failed_files.append((file_path, str(e)))
            return False

        finally:
            # Ensure all temporary chunks are cleaned up
            if chunks:  # Only try to clean up if chunks were created
                for chunk in chunks:
                    if os.path.exists(chunk):
                        os.remove(chunk)

    def save_transcription(self, output_file, input_file, transcription):
        """Save transcription to file with metadata"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcription of: {os.path.basename(input_file)}\n")
                f.write(f"Transcribed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n\n")
                f.write(transcription.text)
                
                if hasattr(transcription, 'segments'):
                    f.write("\n\n" + "-" * 50 + "\n")
                    f.write("Detailed segments:\n")
                    for segment in transcription.segments:
                        start_time = segment.get('start', 0)
                        end_time = segment.get('end', 0)
                        text = segment.get('text', '')
                        f.write(f"\n[{start_time:.2f}s - {end_time:.2f}s]: {text}")
        except Exception as e:
            logging.error(f"Error saving transcription to {output_file}: {e}")
            raise

    def process_failed_files(self):
        """Process only the files that failed in the previous run"""
        if not self.failed_files:
            logging.info("No failed files to process.")
            return

        logging.info(f"\nRetrying {len(self.failed_files)} failed files...")
        still_failed = []
        
        for file_path, error in self.failed_files:
            if os.path.exists(file_path):
                logging.info(f"\nRetrying: {os.path.basename(file_path)}")
                logging.info(f"Previous error: {error}")
                if not self.transcribe_file(file_path):
                    still_failed.append((file_path, error))
        
        self.failed_files = still_failed

def main():
    try:
        # Initialize transcription manager
        manager = TranscriptionManager()
        
        # Define paths
        videos_dir = "Videos"
        supported_extensions = manager.get_supported_extensions()
        
        # Check if Videos directory exists
        if not os.path.exists(videos_dir):
            logging.info(f"Creating {videos_dir} directory...")
            os.makedirs(videos_dir)
            logging.info(f"Please place your video files in the {videos_dir} directory and run the script again.")
            return
        
        # Get failed files from previous run if they exist
        failed_files_path = "failed_files.txt"
        if os.path.exists(failed_files_path):
            with open(failed_files_path, 'r') as f:
                for line in f:
                    file_path, error = line.strip().split('|')
                    if os.path.exists(file_path):
                        manager.failed_files.append((file_path, error))
            
            if manager.failed_files:
                logging.info(f"Found {len(manager.failed_files)} previously failed files.")
                manager.process_failed_files()
                return

        # Get all supported files in the Videos directory
        files_to_transcribe = []
        for file in os.listdir(videos_dir):
            if any(file.lower().endswith(ext) for ext in supported_extensions):
                files_to_transcribe.append(os.path.join(videos_dir, file))
        
        if not files_to_transcribe:
            logging.info(f"No supported files found in {videos_dir} directory.")
            logging.info(f"Supported formats: {', '.join(supported_extensions)}")  # Fixed logging syntax
            return
        
        logging.info(f"Found {len(files_to_transcribe)} files to transcribe.")
        logging.info("Starting transcription process...")
        
        # Process each file
        successful = 0
        for file_path in files_to_transcribe:
            if manager.transcribe_file(file_path):
                successful += 1
        
        # Save failed files for later retry
        if manager.failed_files:
            with open(failed_files_path, 'w') as f:
                for file_path, error in manager.failed_files:
                    f.write(f"{file_path}|{error}\n")
            logging.info(f"\nSaved {len(manager.failed_files)} failed files to {failed_files_path}")
        
        # Print summary
        logging.info("\nTranscription complete!")
        logging.info(f"Successfully transcribed {successful} out of {len(files_to_transcribe)} files.")
        if manager.failed_files:
            logging.info(f"Failed to transcribe {len(manager.failed_files)} files.")
            logging.info("Run the script again to retry failed files.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
