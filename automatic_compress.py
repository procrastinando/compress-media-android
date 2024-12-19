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

# Function to compress video
def compress_video(input_file, output_file, video_bitrate, audio_bitrate):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-c:v", "libx265", "-b:v", f"{video_bitrate}k",
        "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
        output_file
    ])

# Function to compress image
def compress_image(input_file, output_file, quality):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-q:v", str(quality), output_file
    ])

# User inputs
input_dir = "/storage/emulated/0/DCIM/Camera"
output_dir = "/storage/emulated/0/DCIM/Compressed"
video_bitrate=2400
audio_bitrate=128
quality=10
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
            if current_bitrate > 2400:
                compress_video(input_path, output_path, video_bitrate, audio_bitrate)
                os.remove(input_path)

        elif file.lower().endswith((".jpg", ".jpeg")):
            compress_image(input_path, output_path, quality)
            os.remove(input_path)

    time.sleep(period)
