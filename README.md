# Video Transcription Tool

A Python application that transcribes video files using OpenAI's Whisper API. This tool can handle large files, implements retry logic for API errors, and provides detailed transcriptions with timestamps.

## Features

- Batch process multiple video/audio files
- Handle files larger than 25MB by automatically splitting them
- Implement retry logic for API quota errors
- Save transcriptions with timestamps and metadata
- Track and retry failed transcriptions
- Comprehensive logging system

## Supported Formats

- MP3
- MP4
- MPEG
- MPGA
- M4A
- WAV
- WEBM

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio processing)
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/video-transcription-tool.git
cd video-transcription-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file with your OpenAI API key:
```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

## Usage

1. Place your video files in the `Videos` directory

2. Run the transcription script:
```bash
python transcribe_videos_retry.py
```

3. Find your transcriptions in the `Transcriptions` directory

## Error Handling

The tool includes comprehensive error handling:
- Retries on API quota errors
- Handles large files by splitting them
- Saves failed files for later retry
- Provides detailed error logging

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the Whisper API
- FFmpeg for audio processing
- Python community for various libraries used
