import subprocess
import os
import re
import time
from datetime import datetime

# Function to get file age in minutes
def get_file_age(file_path):
    file_time = os.path.getmtime(file_path)
    current_time = time.time()
    return (current_time - file_time) / 60

# Function to get video bitrate
def get_video_bitrate(file_path):
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", file_path],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True
        )
        match = re.search(r"bitrate:\s(\d+)\s", result.stderr)
        bitrate = int(match.group(1)) if match else 0
        return bitrate
    except Exception as e:
        return 0

# Function to compress video while preserving metadata
def compress_video(input_file, output_file, video_bitrate, audio_bitrate):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-map_metadata", "0",  # Copy global metadata
        "-movflags", "use_metadata_tags",  # Ensure metadata is written in a compatible format
        "-c:v", "libx265", "-b:v", f"{video_bitrate}k",  # Compress video
        "-c:a", "aac", "-b:a", f"{audio_bitrate}k",  # Compress audio
        "-tag:v", "hvc1",  # Ensure compatibility with players
        output_file
    ], check=True)
def copy_metadata(input_file, output_file):
    subprocess.run([
        "exiftool", "-TagsFromFile", input_file,
        "-all:all>all:all", output_file,
        "-overwrite_original"
    ], check=True)
def compress_and_preserve_metadata(input_file, output_file, video_bitrate, audio_bitrate):
    # Step 1: Compress the video
    compress_video(input_file, output_file, video_bitrate, audio_bitrate)
    
    # Step 2: Copy metadata from the original to the compressed video
    copy_metadata(input_file, output_file)

# Function to compress image while preserving metadata
def compress_image(input_file, output_file, quality):
    # Keep the correct file extension for the temporary file
    temp_output = f"{os.path.splitext(output_file)[0]}_temp{os.path.splitext(output_file)[1]}"
    
    # Use ffmpeg to compress the image
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-q:v", str(quality), "-f", "image2", temp_output
    ], check=True)
    
    # Copy all metadata from the original to the compressed file using ExifTool
    subprocess.run([
        "exiftool", "-TagsFromFile", input_file,
        "-all:all>all:all", temp_output,
        "-overwrite_original"
    ], check=True)
    
    # Move the temporary file to the final output location
    os.replace(temp_output, output_file)

# User inputs
input_dir = "/storage/emulated/0/DCIM/Camera"
output_dir = "/storage/emulated/0/DCIM/Compressed"
video_bitrate = 2400
audio_bitrate = 128
quality = 10
period = 10
file_age_threshold = 60

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

while True:
    for file in os.listdir(input_dir):
        if file.startswith("."):  # Skip hidden files
            continue

        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, file)
        file_age = get_file_age(input_path)

        if file_age < file_age_threshold:
            continue

        if file.lower().endswith(".mp4"):
            current_bitrate = get_video_bitrate(input_path)
            if current_bitrate > video_bitrate:
                compress_and_preserve_metadata(input_path, output_path, video_bitrate, audio_bitrate)
                os.remove(input_path)

        elif file.lower().endswith((".jpg", ".jpeg")):
            compress_image(input_path, output_path, quality)
            os.remove(input_path)

    time.sleep(period)
