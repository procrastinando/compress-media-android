import subprocess
import os
import re
import time
from datetime import datetime

def read_config(config_path):
    """
    Read configuration from the specified config file.
    Ignores empty lines and comments.
    """
    config = {}
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading config file: {e}")
    return config

def safe_int(value, default):
    """
    Try to convert a value to an integer; if it fails, return the default.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default):
    """
    Try to convert a value to a float; if it fails, return the default.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_video_bitrate(file_path):
    """
    Use ffmpeg to retrieve the video bitrate from the file.
    """
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
        print(f"Error getting video bitrate for {file_path}: {e}")
        return 0

def compress_video(input_file, output_file, video_bitrate, audio_bitrate):
    """
    Compress the video while preserving metadata using ffmpeg.
    """
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-map_metadata", "0",              # Copy global metadata
            "-movflags", "use_metadata_tags",  # Write metadata in a compatible format
            "-c:v", "libx265", "-b:v", f"{video_bitrate}k",
            "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
            "-tag:v", "hvc1",                  # Compatibility with players
            output_file
        ], check=True)
    except Exception as e:
        print(f"Error compressing video {input_file}: {e}")
        raise

def copy_metadata(input_file, output_file):
    """
    Copy metadata from the input file to the output file using ExifTool.
    """
    try:
        subprocess.run([
            "exiftool", "-TagsFromFile", input_file,
            "-all:all>all:all", output_file,
            "-overwrite_original"
        ], check=True)
    except Exception as e:
        print(f"Error copying metadata from {input_file} to {output_file}: {e}")
        raise

def compress_and_preserve_metadata(input_file, output_file, video_bitrate, audio_bitrate):
    """
    Compress the video and then copy the metadata.
    """
    compress_video(input_file, output_file, video_bitrate, audio_bitrate)
    copy_metadata(input_file, output_file)

def compress_image(input_file, output_file, quality):
    """
    Compress an image using ffmpeg and then copy its metadata using ExifTool.
    """
    base, ext = os.path.splitext(output_file)
    temp_output = f"{base}_temp{ext}"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-q:v", str(quality), "-f", "image2", temp_output
        ], check=True)
        subprocess.run([
            "exiftool", "-TagsFromFile", input_file,
            "-all:all>all:all", temp_output,
            "-overwrite_original"
        ], check=True)
        os.replace(temp_output, output_file)
    except Exception as e:
        print(f"Error compressing image {input_file}: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        raise

if __name__ == "__main__":
    # Define the path for the configuration file.
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")
    
    # Default configuration values
    DEFAULT_INPUT_DIR = "/storage/emulated/0/DCIM/Camera"
    DEFAULT_OUTPUT_DIR = "/storage/emulated/0/DCIM/Compressed"
    DEFAULT_VIDEO_BITRATE = 3000
    DEFAULT_AUDIO_BITRATE = 192
    DEFAULT_QUALITY = 7
    DEFAULT_TIME_FROM = 23.5
    DEFAULT_TIME_TO = 7.25

    while True:
        config = read_config(CONFIG_PATH)

        # Retrieve and safely convert configuration values
        input_dir    = config.get("input_dir", DEFAULT_INPUT_DIR)
        output_dir   = config.get("output_dir", DEFAULT_OUTPUT_DIR)
        video_bitrate = safe_int(config.get("video_bitrate"), DEFAULT_VIDEO_BITRATE)
        audio_bitrate = safe_int(config.get("audio_bitrate"), DEFAULT_AUDIO_BITRATE)
        quality      = safe_int(config.get("quality"), DEFAULT_QUALITY)
        time_from    = safe_float(config.get("time_from"), DEFAULT_TIME_FROM)
        time_to      = safe_float(config.get("time_to"), DEFAULT_TIME_TO)

        os.makedirs(output_dir, exist_ok=True)

        now = datetime.now()
        current_hour = now.hour + now.minute / 60.0

        # Determine if the current time is within the allowed conversion window.
        if time_from < time_to:
            allowed = time_from <= current_hour < time_to
        else:
            allowed = current_hour >= time_from or current_hour < time_to

        if allowed:
            for file in os.listdir(input_dir):
                if file.startswith("."):
                    continue

                input_path = os.path.join(input_dir, file)
                output_path = os.path.join(output_dir, file)

                if file.lower().endswith(".mp4"):
                    current_bitrate = get_video_bitrate(input_path)
                    if current_bitrate > video_bitrate:
                        try:
                            compress_and_preserve_metadata(input_path, output_path, video_bitrate, audio_bitrate)
                            os.remove(input_path)
                        except Exception as e:
                            print(f"Error processing video {input_path}: {e}")
                elif file.lower().endswith((".jpg", ".jpeg")):
                    try:
                        compress_image(input_path, output_path, quality)
                        os.remove(input_path)
                    except Exception as e:
                        print(f"Error processing image {input_path}: {e}")
        else:
            print("Current time is outside the conversion window. Waiting...")

        time.sleep(60)
