import os
from pathlib import Path
import re
from collections import defaultdict

def extract_base_name(filename):
    # Extract the base name before the timestamp
    match = re.match(r'(.+)_\d{8}_\d{6}\.txt$', filename)
    return match.group(1) if match else None

def cleanup_duplicates(directory):
    # Group files by their base name
    file_groups = defaultdict(list)
    
    # List all .txt files in the directory
    for file in os.listdir(directory):
        if file.endswith('.txt'):
            base_name = extract_base_name(file)
            if base_name:
                full_path = os.path.join(directory, file)
                file_groups[base_name].append(full_path)
    
    # Keep track of deleted and kept files
    deleted_count = 0
    kept_files = []
    
    # For each group of files with the same base name
    for base_name, files in file_groups.items():
        if len(files) > 1:
            # Sort files by modification time, newest first
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Keep the newest file
            kept_file = files[0]
            kept_files.append(os.path.basename(kept_file))
            
            # Delete older versions
            for file in files[1:]:
                try:
                    os.remove(file)
                    deleted_count += 1
                    print(f"Deleted: {os.path.basename(file)}")
                except Exception as e:
                    print(f"Error deleting {file}: {e}")
    
    print(f"\nCleanup complete!")
    print(f"Deleted {deleted_count} duplicate files.")
    print(f"Kept {len(kept_files)} unique transcriptions.")

if __name__ == "__main__":
    transcriptions_dir = "Transcriptions"
    if not os.path.exists(transcriptions_dir):
        print(f"Error: {transcriptions_dir} directory not found!")
    else:
        cleanup_duplicates(transcriptions_dir)
