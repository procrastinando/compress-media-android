import subprocess
import os
import re

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
        print(f"The bitrate of the video {file_path} is: {bitrate} kbps")
        return bitrate
    except Exception as e:
        print(f"Error getting bitrate for video {file_path}: {e}")
        return 0

# Function to compress video
def compress_video(input_file, output_file, video_bitrate=2400, audio_bitrate=128):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "libx265", "-b:v", f"{video_bitrate}k",
            "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
            output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Compressed video saved to: {output_file}")
    except Exception as e:
        print(f"Error compressing video {input_file}: {e}")

# Function to compress image
def compress_image(input_file, output_file, quality=10):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-q:v", str(quality), output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Compressed image saved to: {output_file}")
    except Exception as e:
        print(f"Error compressing image {input_file}: {e}")

# User inputs
input_dir = input("Enter input directory (default: /storage/emulated/0/DCIM/Camera): ") or "/storage/emulated/0/DCIM/Camera"
output_dir = input("Enter output directory (default: /storage/emulated/0/DCIM/Compressed): ") or "/storage/emulated/0/DCIM/Compressed"
video_bitrate_threshold = int(input("Enter video bitrate threshold in kbps (default: 2400): ") or 2400)
audio_bitrate_threshold = int(input("Enter audio bitrate threshold in kbps (default: 128): ") or 128)
image_quality = int(input("Enter image quality for JPEG (default: 10): ") or 10)
delete_original = "yes"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Process files
for file in os.listdir(input_dir):
    if file.startswith("."):  # Skip hidden files
        continue

    input_path = os.path.join(input_dir, file)
    output_path = os.path.join(output_dir, file)

    if file.lower().endswith(".mp4"):
        current_bitrate = get_video_bitrate(input_path)
        if current_bitrate > video_bitrate_threshold:
            print(f"Compressing video: {file}")
            compress_video(input_path, output_path, video_bitrate_threshold, audio_bitrate_threshold)
            if delete_original == "yes" and os.path.exists(output_path):
                os.remove(input_path)
        else:
            print(f"Skipping video {file} as its bitrate is lower than {video_bitrate_threshold} kbps")

    elif file.lower().endswith((".jpg", ".jpeg")):
        print(f"Compressing image: {file}")
        compress_image(input_path, output_path, image_quality)
        if delete_original == "yes" and os.path.exists(output_path):
            os.remove(input_path)

print("Compression completed!")
