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
        print(f"Error reading config file {config_path}: {e}")
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
        # Use ffprobe for more reliable bitrate extraction
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            capture_output=True, text=True, check=True
        )
        bitrate_bps = int(result.stdout.strip())
        # Convert bits per second to kilobits per second
        return bitrate_bps / 1000
    except subprocess.CalledProcessError as e:
        # Check if the error is due to no bitrate info (e.g., image, audio-only)
        if "N/A" in e.stderr or "bit_rate=N/A" in e.stdout:
             print(f"No video bitrate found for {file_path}. Assuming 0.")
             return 0
        # Check ffprobe stderr for specific bitrate parsing errors (less common)
        stderr_output = e.stderr.lower()
        match = re.search(r"bitrate:\s+(\d+)\s+kb/s", stderr_output) # Fallback regex on error output
        if match:
             print(f"Using fallback regex on ffprobe error output for {file_path}.")
             return int(match.group(1))

        print(f"Error getting video bitrate for {file_path} using ffprobe: {e}")
        print(f"ffprobe stdout: {e.stdout}")
        print(f"ffprobe stderr: {e.stderr}")
        # Fallback to ffmpeg method if ffprobe fails unexpectedly
        try:
            print(f"Falling back to ffmpeg -i for bitrate for {file_path}")
            result_ffmpeg = subprocess.run(
                ["ffmpeg", "-i", file_path],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True
            )
            # More robust regex for ffmpeg output
            match_ffmpeg = re.search(r"bitrate:\s*(\d+)\s*kb/s", result_ffmpeg.stderr, re.IGNORECASE)
            bitrate_kbps = int(match_ffmpeg.group(1)) if match_ffmpeg else 0
            print(f"Fallback ffmpeg bitrate found: {bitrate_kbps} kb/s")
            return bitrate_kbps
        except Exception as e_ffmpeg:
            print(f"Fallback ffmpeg method also failed for {file_path}: {e_ffmpeg}")
            return 0
    except FileNotFoundError:
        print(f"Error: ffprobe command not found. Please ensure ffprobe (part of FFmpeg) is installed and in your PATH.")
        return 0
    except Exception as e:
        print(f"Unexpected error getting video bitrate for {file_path}: {e}")
        return 0


def compress_video(input_file, output_file, video_bitrate, audio_bitrate):
    """
    Compress the video while preserving metadata using ffmpeg.
    """
    try:
        print(f"Compressing video: {input_file} -> {output_file} (V:{video_bitrate}k, A:{audio_bitrate}k)")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-map_metadata", "0",              # Copy global metadata
            "-movflags", "+use_metadata_tags", # Correct flag syntax for writing metadata
            "-c:v", "libx265", "-b:v", f"{video_bitrate}k",
            "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
            "-tag:v", "hvc1",                  # Compatibility tag
            output_file
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) # Capture output for debugging
        print(f"Successfully compressed video: {input_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error compressing video {input_file}: {e}")
        print(f"FFmpeg stdout: {e.stdout.decode(errors='ignore')}")
        print(f"FFmpeg stderr: {e.stderr.decode(errors='ignore')}")
        # Attempt to clean up partially created output file on error
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"Removed incomplete output file: {output_file}")
            except OSError as remove_err:
                print(f"Error removing incomplete output file {output_file}: {remove_err}")
        raise # Re-raise the exception to be caught by the main loop
    except FileNotFoundError:
        print(f"Error: ffmpeg command not found. Please ensure ffmpeg is installed and in your PATH.")
        raise
    except Exception as e:
        print(f"Unexpected error compressing video {input_file}: {e}")
        raise

def copy_metadata(input_file, output_file):
    """
    Copy metadata from the input file to the output file using ExifTool.
    Ensures the output file exists before attempting copy.
    """
    if not os.path.exists(output_file):
        print(f"Error: Output file {output_file} does not exist. Cannot copy metadata.")
        # Raise an error because metadata copy is expected after successful compression
        raise FileNotFoundError(f"Output file {output_file} missing for metadata copy.")

    try:
        print(f"Copying metadata from {input_file} to {output_file}")
        # Use -m to ignore minor errors, which can sometimes occur with video metadata
        # Removed -overwrite_original as it applies to the *source* file (-TagsFromFile target)
        # Instead, exiftool modifies the *last* file specified on the command line (output_file)
        result = subprocess.run([
            "exiftool", "-m", "-TagsFromFile", input_file,
            "-all:all>all:all", "-unsafe", # Allow writing potentially unsafe tags often found in video
            output_file + "_original" # Backup automatically created by exiftool
        ], check=True, capture_output=True, text=True) # Capture output
        print(f"Successfully copied metadata for: {output_file}")
         # Exiftool creates a backup file ending with _original. Remove it.
        backup_file = output_file + "_original"
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except OSError as e:
                print(f"Warning: Could not remove exiftool backup file {backup_file}: {e}")

    except subprocess.CalledProcessError as e:
        print(f"Error copying metadata from {input_file} to {output_file} using ExifTool: {e}")
        print(f"ExifTool stdout: {e.stdout}")
        print(f"ExifTool stderr: {e.stderr}")
        # Decide if this is a fatal error. Often, some metadata warnings occur.
        # If the main goal is achieved (compression), maybe just log this.
        # However, raising makes it clear the process wasn't perfect.
        raise # Re-raise the exception
    except FileNotFoundError:
         print(f"Error: exiftool command not found. Please ensure ExifTool is installed and in your PATH.")
         raise
    except Exception as e:
        print(f"Unexpected error copying metadata for {output_file}: {e}")
        raise

def compress_and_preserve_metadata(input_file, output_file, video_bitrate, audio_bitrate):
    """
    Compress the video and then copy the metadata.
    Handles potential errors during compression or metadata copy.
    """
    try:
        compress_video(input_file, output_file, video_bitrate, audio_bitrate)
        copy_metadata(input_file, output_file)
        # If both succeed, remove the original input file
        try:
            os.remove(input_file)
            print(f"Successfully processed and removed original: {input_file}")
        except OSError as e:
            print(f"Error removing original file {input_file} after processing: {e}")
            # Don't raise here, as the main task (compression+metadata) succeeded

    except Exception as e:
        # Error logged in compress_video or copy_metadata
        print(f"Failed to process {input_file} due to error: {e}")
        # Do not remove input_file if any step failed
        # Ensure potential partial output file from failed compression is removed
        if os.path.exists(output_file):
            try:
                # Check if the exception came from copy_metadata after successful compress_video
                # If compress_video failed, it should have cleaned up its output already.
                # This check is a bit redundant given compress_video's cleanup, but safe.
                 if not isinstance(e, FileNotFoundError) or e.filename != output_file: # Avoid removing if copy_metadata failed because output didn't exist
                    os.remove(output_file)
                    print(f"Removed potentially incomplete output file due to error: {output_file}")
            except OSError as remove_err:
                print(f"Error removing output file {output_file} after processing error: {remove_err}")
        # Re-raise the exception so the main loop knows this file failed
        raise

def compress_image(input_file, output_file, quality):
    """
    Compress an image using ffmpeg and then copy its metadata using ExifTool.
    Uses a temporary file for ffmpeg output before metadata copy.
    """
    base, ext = os.path.splitext(output_file)
    # Use a more unique temporary file name in case of concurrent runs or crashes
    temp_output = f"{base}_temp_{os.getpid()}{ext}"

    try:
        print(f"Compressing image: {input_file} -> {output_file} (Quality: {quality})")
        # Run ffmpeg to compress to temporary file
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-q:v", str(quality), # Quality scale for lossy formats like JPEG
            "-f", "image2",       # Ensure output format is image
            temp_output
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) # Capture output
        print(f"Successfully created temp compressed image: {temp_output}")

        # Copy metadata from original to temporary file using ExifTool
        print(f"Copying metadata from {input_file} to {temp_output}")
        # Use -m to ignore minor errors, -overwrite_original modifies temp_output
        result = subprocess.run([
            "exiftool", "-m", "-TagsFromFile", input_file,
            "-all:all>all:all", "-unsafe",
            temp_output + "_original" # Creates backup automatically
        ], check=True, capture_output=True, text=True)
        print(f"Successfully copied metadata to temp file: {temp_output}")

         # Remove exiftool backup
        backup_file = temp_output + "_original"
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except OSError as e:
                 print(f"Warning: Could not remove exiftool backup file {backup_file}: {e}")

        # Rename the temporary file to the final output file
        os.replace(temp_output, output_file)
        print(f"Successfully finalized image: {output_file}")

        # If all succeeds, remove the original input file
        try:
            os.remove(input_file)
            print(f"Successfully processed and removed original: {input_file}")
        except OSError as e:
            print(f"Error removing original file {input_file} after processing: {e}")

    except subprocess.CalledProcessError as e:
        print(f"Error during image processing step for {input_file}: {e}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Stdout: {e.stdout.decode(errors='ignore')}")
        print(f"Stderr: {e.stderr.decode(errors='ignore')}")
        # Clean up temporary file if it exists
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
                print(f"Removed temporary image file: {temp_output}")
            except OSError as remove_err:
                print(f"Error removing temporary image file {temp_output}: {remove_err}")
        # Re-raise the exception
        raise
    except FileNotFoundError as e:
        print(f"Error: Required command not found (ffmpeg or exiftool). Please ensure they are installed and in your PATH.")
        print(f"Missing command detail: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error compressing image {input_file}: {e}")
        # Clean up temporary file if it exists
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
                print(f"Removed temporary image file due to unexpected error: {temp_output}")
            except OSError as remove_err:
                print(f"Error removing temporary image file {temp_output} after error: {remove_err}")
        raise
    finally:
        # Ensure temporary exiftool backup is removed if it somehow still exists
        backup_file = temp_output + "_original"
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except OSError as e:
                print(f"Warning: Could not remove exiftool backup file in finally block {backup_file}: {e}")


if __name__ == "__main__":
    # Define the path for the configuration file relative to the script location.
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.txt")

    # --- Default configuration values ---
    DEFAULT_INPUT_DIRS = [
        "/storage/emulated/0/DCIM/Camera"
        ]
    DEFAULT_OUTPUT_DIR = "/storage/emulated/0/DCIM/Compressed"
    DEFAULT_VIDEO_BITRATE = 3000 # kbps
    DEFAULT_AUDIO_BITRATE = 192  # kbps
    DEFAULT_IMAGE_QUALITY = 7    # Quality scale for ffmpeg (lower means smaller/lower quality, depends on codec)
    DEFAULT_TIME_FROM = 23.5     # 11:30 PM
    DEFAULT_TIME_TO = 7.25       # 7:15 AM

    print("Script started. Press Ctrl+C to stop.")
    print(f"Using config file: {CONFIG_PATH}")

    while True:
        try:
            config = read_config(CONFIG_PATH)

            # --- Retrieve and safely convert configuration values ---

            # Handle input directories (expects comma-separated string in config)
            input_dirs_str = config.get("input_dirs") # Read as string first
            if input_dirs_str:
                # Split by comma, strip whitespace from each path, filter out empty strings
                input_dirs = [d.strip() for d in input_dirs_str.split(',') if d.strip()]
                if not input_dirs: # Handle case where config line is like "input_dirs="
                    print("Warning: 'input_dirs' key found in config but value is empty or only whitespace. Using default.")
                    input_dirs = DEFAULT_INPUT_DIRS
            else:
                 # Use default if key is not in config file
                 input_dirs = DEFAULT_INPUT_DIRS

            output_dir   = config.get("output_dir", DEFAULT_OUTPUT_DIR)
            # Use descriptive names matching config keys where possible
            video_bitrate_target = safe_int(config.get("video_bitrate_target"), DEFAULT_VIDEO_BITRATE)
            audio_bitrate_target = safe_int(config.get("audio_bitrate_target"), DEFAULT_AUDIO_BITRATE)
            image_quality        = safe_int(config.get("image_quality"), DEFAULT_IMAGE_QUALITY)
            time_from            = safe_float(config.get("time_from"), DEFAULT_TIME_FROM)
            time_to              = safe_float(config.get("time_to"), DEFAULT_TIME_TO)

            # --- Prepare output directory ---
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                print(f"Error: Could not create output directory {output_dir}: {e}. Exiting loop iteration.")
                time.sleep(60)
                continue # Skip the rest of this iteration

            # --- Check time window ---
            now = datetime.now()
            current_hour_float = now.hour + now.minute / 60.0 + now.second / 3600.0

            # Determine if the current time is within the allowed conversion window.
            # Handles overnight window (e.g., from 23:00 to 07:00)
            if time_from < time_to: # Normal window (e.g., 9.0 to 17.0)
                allowed = time_from <= current_hour_float < time_to
            else: # Overnight window (e.g., 23.0 to 7.0)
                allowed = current_hour_float >= time_from or current_hour_float < time_to

            if allowed:
                print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} - Within allowed time window ({time_from:.2f} - {time_to:.2f}). Checking for files...")

                # --- Iterate through each configured input directory ---
                files_processed_this_cycle = 0
                for current_input_dir in input_dirs:
                    # Check if the input directory exists and is actually a directory
                    if not os.path.isdir(current_input_dir):
                        print(f"Warning: Input directory not found or not a directory: {current_input_dir}. Skipping.")
                        continue # Skip to the next directory in the list

                    print(f"Scanning directory: {current_input_dir}")

                    # --- Iterate through files in the current input directory ---
                    try:
                        files_in_dir = os.listdir(current_input_dir)
                    except OSError as e:
                        print(f"Error listing files in directory {current_input_dir}: {e}. Skipping directory.")
                        continue

                    for filename in files_in_dir:
                        # Ignore hidden files/folders
                        if filename.startswith("."):
                            continue

                        input_path = os.path.join(current_input_dir, filename)
                        # Place all output files directly into the single output_dir
                        # Potential for name collisions if files with the same name exist in different input dirs.
                        # Consider adding subdirectory structure to output if this is a concern.
                        output_path = os.path.join(output_dir, filename)

                        # Check if it's a file (and not a directory)
                        if not os.path.isfile(input_path):
                            continue

                        # Check if the output file already exists (avoids reprocessing/errors)
                        if os.path.exists(output_path):
                            # print(f"Skipping {filename}: Output file already exists at {output_path}")
                            continue # Skip this file, already processed or manually placed

                        lower_filename = filename.lower()

                        # --- Process MP4 videos ---
                        if lower_filename.endswith(".mp4"):
                            print(f"Found video: {filename}")
                            current_bitrate_kbps = get_video_bitrate(input_path)
                            print(f"  - Current bitrate: {current_bitrate_kbps:.2f} kbps (Target: {video_bitrate_target} kbps)")
                            # Only compress if current bitrate is significantly higher (e.g., > 10% higher) to avoid recompressing already compressed files
                            # Or if bitrate couldn't be determined (returns 0)
                            if current_bitrate_kbps == 0 or current_bitrate_kbps > video_bitrate_target * 1.1:
                                try:
                                    compress_and_preserve_metadata(input_path, output_path, video_bitrate_target, audio_bitrate_target)
                                    files_processed_this_cycle += 1
                                    # Input file is removed by compress_and_preserve_metadata on success
                                except Exception as e:
                                    print(f"Failed to process video {input_path}. Error logged above. File not removed.")
                                    # Error is already logged inside the function
                            else:
                                print(f"  - Skipping compression for {filename}: Bitrate ({current_bitrate_kbps:.2f}k) is not significantly higher than target ({video_bitrate_target}k).")
                                # Decide whether to move the file anyway or leave it. Let's move it without compression.
                                try:
                                    print(f"  - Moving file {filename} to output directory without compression.")
                                    os.rename(input_path, output_path)
                                except OSError as e:
                                     print(f"  - Error moving file {input_path} to {output_path}: {e}")


                        # --- Process JPG/JPEG images ---
                        elif lower_filename.endswith((".jpg", ".jpeg")):
                            print(f"Found image: {filename}")
                            try:
                                compress_image(input_path, output_path, image_quality)
                                files_processed_this_cycle += 1
                                # Input file is removed by compress_image on success
                            except Exception as e:
                                print(f"Failed to process image {input_path}. Error logged above. File not removed.")
                                # Error is already logged inside the function

                        # Add more file types here if needed (e.g., .png, .mov)

                if files_processed_this_cycle > 0:
                     print(f"Finished processing cycle. {files_processed_this_cycle} file(s) processed.")
                else:
                     print("No new files to process in allowed directories.")

            else:
                print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} - Current time is outside the allowed window ({time_from:.2f} - {time_to:.2f}). Waiting...")

            # --- Wait before the next check ---
            sleep_duration = 60 # seconds
            print(f"Sleeping for {sleep_duration} seconds...")
            time.sleep(sleep_duration)

        except KeyboardInterrupt:
            print("\nScript interrupted by user. Exiting.")
            break
        except Exception as e:
            # Catch unexpected errors in the main loop
            print(f"\n--- UNEXPECTED ERROR IN MAIN LOOP ---")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print("-------------------------------------")
            print("Continuing loop after 60 seconds...")
            time.sleep(60)