import subprocess
import os
import re
import time
from datetime import datetime
import traceback # Added for logging tracebacks

# --- Global Log File Path ---
LOG_FILE_PATH = ""

# --- Default configuration values ---
DEFAULT_INPUT_DIRS = ["/storage/emulated/0/DCIM/Camera"]
DEFAULT_OUTPUT_DIR = "/storage/emulated/0/DCIM/Compressed"
DEFAULT_VIDEO_BITRATE = 3000
DEFAULT_AUDIO_BITRATE = 192
DEFAULT_IMAGE_QUALITY = 7
DEFAULT_TIME_FROM = 23.5
DEFAULT_TIME_TO = 7.25
DEFAULT_SLEEP_DURATION = 60

def setup_logging(script_dir):
    """Initializes the path for the log file."""
    global LOG_FILE_PATH
    LOG_FILE_PATH = os.path.join(script_dir, "logs.txt")
    # First log message to confirm log file is being used
    log_message(f"Logging initialized. Log file: {LOG_FILE_PATH}")

def log_message(message):
    """Appends a timestamped message to the log file."""
    global LOG_FILE_PATH
    if not LOG_FILE_PATH: # Should not happen if setup_logging is called first
        print(f"ERROR: LOG_FILE_PATH not set. Message: {message}") # Fallback to print if logging not set up
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{now_str}] {message}\n"
    try:
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        # If logging fails, there's no terminal to print to.
        # This is a critical failure of the logging mechanism itself.
        # We can't do much other than try to print to stderr once as a last resort.
        # Subsequent logging attempts will also fail.
        # To strictly avoid terminal, we might have to ignore this.
        # For now, print a single error message to stderr if this occurs.
        if not hasattr(log_message, "logging_error_reported"):
            print(f"CRITICAL LOGGING ERROR: Could not write to {LOG_FILE_PATH}. Error: {e}. Further log messages may be lost.", file=os.sys.stderr)
            log_message.logging_error_reported = True # Avoid spamming stderr
        pass # Continue execution even if logging fails

def read_config_yaml(config_path):
    config = {}
    reading_input_dirs = False
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line_content in enumerate(f, 1):
                line = line_content.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("input_dir:"):
                    config["input_dir"] = []
                    reading_input_dirs = True
                    _, _, value_on_line = line.partition(":")
                    if value_on_line.strip():
                        log_message(f"Warning in '{config_path}' (line {line_num}): 'input_dir:' should be followed by list items on new lines. Ignoring value: '{value_on_line.strip()}'")
                    continue
                if reading_input_dirs:
                    if line.startswith("- "):
                        item = line[1:].strip()
                        if item:
                            config["input_dir"].append(item)
                        continue
                    else:
                        reading_input_dirs = False
                if ":" in line:
                    key, value = line.split(":", 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        log_message(f"Info: Config file '{config_path}' not found. Default values will be used.")
        return {}
    except Exception as e:
        log_message(f"Error reading or parsing config file '{config_path}': {e}. Default values will be used.")
        return {}
    return config

def safe_int(value, default):
    try:
        return int(value)
    except (ValueError, TypeError, AttributeError):
        return default

def safe_float(value, default):
    try:
        return float(value)
    except (ValueError, TypeError, AttributeError):
        return default

def get_video_bitrate(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore'
        )
        bitrate_str = result.stdout.strip()
        if bitrate_str == "N/A":
            log_message(f"  Info: No video bitrate found for '{os.path.basename(file_path)}' (ffprobe reported N/A). Assuming 0 kbps.")
            return 0
        bitrate_bps = int(bitrate_str)
        return bitrate_bps / 1000
    except ValueError:
        log_message(f"  Warning: ffprobe returned non-numeric bitrate for '{os.path.basename(file_path)}'. Assuming 0 kbps.")
        return 0
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.strip() if e.stderr else ""
        stdout_output = e.stdout.strip() if e.stdout else ""
        if "N/A" in stderr_output or "bit_rate=N/A" in stdout_output:
             log_message(f"  Info: No video bitrate found for '{os.path.basename(file_path)}' via ffprobe error. Assuming 0 kbps.")
             return 0
        match_error = re.search(r"bitrate:\s+(\d+)\s+kb/s", stderr_output.lower())
        if match_error:
             log_message(f"  Info: Using fallback regex on ffprobe error output for '{os.path.basename(file_path)}'.")
             return int(match_error.group(1))

        log_message(f"  Warning: Error getting video bitrate for '{os.path.basename(file_path)}' using ffprobe: {stderr_output}")
        try:
            log_message(f"  Info: Falling back to 'ffmpeg -i' for bitrate for '{os.path.basename(file_path)}'.")
            result_ffmpeg = subprocess.run(
                ["ffmpeg", "-i", file_path],
                stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding='utf-8', errors='ignore'
            )
            match_ffmpeg = re.search(r"bitrate:\s*(\d+)\s*kb/s", result_ffmpeg.stderr, re.IGNORECASE)
            if match_ffmpeg:
                bitrate_kbps = int(match_ffmpeg.group(1))
                log_message(f"  Info: Fallback 'ffmpeg -i' bitrate found: {bitrate_kbps} kbps.")
                return bitrate_kbps
            else:
                log_message(f"  Warning: Could not find bitrate using 'ffmpeg -i' fallback for '{os.path.basename(file_path)}'. FFmpeg output: {result_ffmpeg.stderr.strip()}")
                return 0
        except Exception as e_ffmpeg:
            log_message(f"  Error: Fallback 'ffmpeg -i' method also failed for '{os.path.basename(file_path)}': {e_ffmpeg}")
            return 0
    except FileNotFoundError:
        log_message(f"Error: 'ffprobe' command not found. Please ensure FFmpeg is installed and in your system PATH.")
        return -1
    except Exception as e:
        log_message(f"  Error: Unexpected error getting video bitrate for '{os.path.basename(file_path)}': {e}")
        return 0

def compress_video(input_file, output_file, target_video_bitrate, target_audio_bitrate):
    log_message(f"  Compressing video: '{os.path.basename(input_file)}' -> '{os.path.basename(output_file)}' (V:{target_video_bitrate}k, A:{target_audio_bitrate}k)")
    try:
        command = [
            "ffmpeg", "-y", "-i", input_file,
            "-map_metadata", "0", "-movflags", "+use_metadata_tags",
            "-c:v", "libx265", "-b:v", f"{target_video_bitrate}k",
            "-c:a", "aac", "-b:a", f"{target_audio_bitrate}k",
            "-tag:v", "hvc1", output_file
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        log_message(f"  Successfully compressed video: '{os.path.basename(input_file)}'")
        if result.stdout.strip(): log_message(f"    FFmpeg stdout: {result.stdout.strip()}")
        if result.stderr.strip(): log_message(f"    FFmpeg stderr (info): {result.stderr.strip()}")
    except subprocess.CalledProcessError as e:
        log_message(f"  Error compressing video '{os.path.basename(input_file)}':")
        log_message(f"    FFmpeg command: {' '.join(e.cmd)}")
        if e.stdout: log_message(f"    FFmpeg stdout: {e.stdout.strip()}")
        if e.stderr: log_message(f"    FFmpeg stderr: {e.stderr.strip()}")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                log_message(f"  Removed incomplete output file: '{output_file}'")
            except OSError as remove_err:
                log_message(f"  Error removing incomplete output file '{output_file}': {remove_err}")
        raise
    except FileNotFoundError:
        log_message(f"Error: 'ffmpeg' command not found. Please ensure FFmpeg is installed and in your system PATH.")
        raise

def copy_metadata_exiftool(input_file, output_file):
    if not os.path.exists(output_file):
        log_message(f"  Error: Output file '{output_file}' does not exist. Cannot copy metadata.")
        raise FileNotFoundError(f"Output file '{output_file}' missing for metadata copy.")

    log_message(f"  Copying metadata using ExifTool: '{os.path.basename(input_file)}' -> '{os.path.basename(output_file)}'")
    try:
        command = [
            "exiftool", "-m", "-TagsFromFile", input_file,
            "-all:all>all:all", "-unsafe", "-overwrite_original", output_file
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        log_message(f"  Successfully copied metadata for: '{os.path.basename(output_file)}'")
        if result.stdout.strip(): log_message(f"    ExifTool stdout: {result.stdout.strip()}")
        # Exiftool with -m might put warnings in stderr but still succeed
        if result.stderr.strip() and "1 image files updated" not in result.stdout: # Common success message
            log_message(f"    ExifTool stderr (info/warning): {result.stderr.strip()}")
    except subprocess.CalledProcessError as e:
        log_message(f"  Error copying metadata for '{os.path.basename(output_file)}' using ExifTool:")
        log_message(f"    ExifTool command: {' '.join(e.cmd)}")
        if e.stdout: log_message(f"    ExifTool stdout: {e.stdout.strip()}")
        if e.stderr: log_message(f"    ExifTool stderr: {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        log_message(f"Error: 'exiftool' command not found. Please ensure ExifTool is installed and in your system PATH.")
        raise

def process_video_file(input_file, output_file, video_bitrate_cfg, audio_bitrate_cfg):
    try:
        compress_video(input_file, output_file, video_bitrate_cfg, audio_bitrate_cfg)
        copy_metadata_exiftool(input_file, output_file)
        try:
            os.remove(input_file)
            log_message(f"  Successfully processed and removed original: '{os.path.basename(input_file)}'")
        except OSError as e:
            log_message(f"  Warning: Error removing original file '{input_file}' after processing: {e}")
    except Exception: # Error already logged by sub-functions
        log_message(f"  Failed to process video '{os.path.basename(input_file)}'. See error details above.")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                log_message(f"  Removed potentially incomplete output file '{output_file}' due to processing error.")
            except OSError as remove_err:
                log_message(f"  Error removing output file '{output_file}' after processing error: {remove_err}")
        raise

def process_image_file(input_file, output_file, image_quality_cfg):
    base, ext = os.path.splitext(output_file)
    temp_output_image = f"{base}_temp_{os.getpid()}{ext}"

    log_message(f"  Processing image: '{os.path.basename(input_file)}' -> '{os.path.basename(output_file)}' (Quality: {image_quality_cfg})")
    try:
        command_ffmpeg = [
            "ffmpeg", "-y", "-i", input_file,
            "-q:v", str(image_quality_cfg), "-f", "image2", temp_output_image
        ]
        result_ffmpeg = subprocess.run(command_ffmpeg, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        log_message(f"  Successfully created temp compressed image: '{os.path.basename(temp_output_image)}'")
        if result_ffmpeg.stdout.strip(): log_message(f"    FFmpeg stdout: {result_ffmpeg.stdout.strip()}")
        if result_ffmpeg.stderr.strip(): log_message(f"    FFmpeg stderr (info): {result_ffmpeg.stderr.strip()}")


        copy_metadata_exiftool(input_file, temp_output_image)
        os.replace(temp_output_image, output_file)
        log_message(f"  Successfully finalized image: '{os.path.basename(output_file)}'")
        try:
            os.remove(input_file)
            log_message(f"  Successfully processed and removed original: '{os.path.basename(input_file)}'")
        except OSError as e:
            log_message(f"  Warning: Error removing original image file '{input_file}' after processing: {e}")
    except subprocess.CalledProcessError as e:
        log_message(f"  Error during image processing step for '{os.path.basename(input_file)}':")
        log_message(f"    Command: {' '.join(e.cmd)}")
        if e.stdout: log_message(f"    Stdout: {e.stdout.strip()}")
        if e.stderr: log_message(f"    Stderr: {e.stderr.strip()}")
        raise
    except FileNotFoundError: # Handled by sub-functions, but re-raise
        log_message(f"  A required command was not found. Processing stopped for '{os.path.basename(input_file)}'.")
        raise
    except Exception as e:
        log_message(f"  Unexpected error compressing image '{os.path.basename(input_file)}': {e}")
        raise
    finally:
        if os.path.exists(temp_output_image):
            try:
                os.remove(temp_output_image)
                log_message(f"  Cleaned up temporary image file: '{temp_output_image}'")
            except OSError as remove_err:
                log_message(f"  Error removing temporary image file '{temp_output_image}' in finally block: {remove_err}")

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    setup_logging(SCRIPT_DIR) # Initialize logging FIRST

    CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")

    log_message("Script started.")
    log_message(f"Using config file: {CONFIG_PATH}")

    ffprobe_found = True
    ffmpeg_found = True
    exiftool_found = True

    while True:
        try:
            raw_config = read_config_yaml(CONFIG_PATH)
            input_dirs   = raw_config.get("input_dir", DEFAULT_INPUT_DIRS)
            if not isinstance(input_dirs, list) or not input_dirs:
                if "input_dir" in raw_config:
                    log_message(f"Warning: 'input_dir' in config was not a valid list or was empty. Using default: {DEFAULT_INPUT_DIRS}")
                input_dirs = DEFAULT_INPUT_DIRS
            output_dir   = raw_config.get("output_dir", DEFAULT_OUTPUT_DIR)
            video_bitrate_target = safe_int(raw_config.get("video_bitrate"), DEFAULT_VIDEO_BITRATE)
            audio_bitrate_target = safe_int(raw_config.get("audio_bitrate"), DEFAULT_AUDIO_BITRATE)
            image_quality_cfg    = safe_int(raw_config.get("quality"), DEFAULT_IMAGE_QUALITY)
            time_from_cfg        = safe_float(raw_config.get("time_from"), DEFAULT_TIME_FROM)
            time_to_cfg          = safe_float(raw_config.get("time_to"), DEFAULT_TIME_TO)
            sleep_duration_cfg   = safe_int(raw_config.get("sleep_duration"), DEFAULT_SLEEP_DURATION)

            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                log_message(f"Error: Could not create output directory '{output_dir}': {e}. Skipping this cycle.")
                time.sleep(sleep_duration_cfg)
                continue

            now = datetime.now()
            current_hour_float = now.hour + now.minute / 60.0
            if time_from_cfg < time_to_cfg:
                is_time_allowed = time_from_cfg <= current_hour_float < time_to_cfg
            else:
                is_time_allowed = current_hour_float >= time_from_cfg or current_hour_float < time_to_cfg

            if is_time_allowed:
                log_message(f"Within allowed time window ({time_from_cfg:.2f} - {time_to_cfg:.2f}). Checking for files...")
                files_processed_this_cycle = 0

                # Check for tool existence once per cycle if not found previously
                if not ffmpeg_found and not os.path.exists(os.path.join(SCRIPT_DIR, ".ffmpeg_checked")):
                    try: subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
                    except FileNotFoundError: log_message("CRITICAL: ffmpeg command not found globally. Processing requiring ffmpeg will fail.")
                    except subprocess.CalledProcessError: ffmpeg_found = True # Found but version call failed, assume ok
                    else: ffmpeg_found = True
                    open(os.path.join(SCRIPT_DIR, ".ffmpeg_checked"), 'a').close() # Mark as checked

                if not exiftool_found and not os.path.exists(os.path.join(SCRIPT_DIR, ".exiftool_checked")):
                    try: subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
                    except FileNotFoundError: log_message("CRITICAL: exiftool command not found globally. Processing requiring exiftool will fail.")
                    except subprocess.CalledProcessError: exiftool_found = True # Found but version call failed, assume ok
                    else: exiftool_found = True
                    open(os.path.join(SCRIPT_DIR, ".exiftool_checked"), 'a').close() # Mark as checked


                for current_input_dir in input_dirs:
                    if not os.path.isdir(current_input_dir):
                        log_message(f"Warning: Input directory not found or not a directory: '{current_input_dir}'. Skipping.")
                        continue
                    
                    log_message(f"Scanning directory: '{current_input_dir}'")
                    try:
                        filenames_in_dir = os.listdir(current_input_dir)
                    except OSError as e:
                        log_message(f"Error listing files in '{current_input_dir}': {e}. Skipping directory.")
                        continue

                    for filename in filenames_in_dir:
                        if filename.startswith("."):
                            continue
                        input_path = os.path.join(current_input_dir, filename)
                        output_path = os.path.join(output_dir, filename)
                        if not os.path.isfile(input_path):
                            continue
                        if os.path.exists(output_path):
                            continue
                        
                        lower_filename = filename.lower()
                        file_processed_successfully = False

                        try:
                            if lower_filename.endswith(".mp4"):
                                log_message(f"Found video: '{filename}'")
                                if not ffmpeg_found : # Relies on ffprobe also being part of ffmpeg installation
                                     log_message(f"  Skipping video '{filename}', ffmpeg/ffprobe not found.")
                                     continue

                                current_br_kbps = get_video_bitrate(input_path)
                                if current_br_kbps == -1: # ffprobe not found error
                                    ffprobe_found = False # Mark specifically ffprobe as not found
                                    ffmpeg_found = False # If ffprobe not found, ffmpeg likely has issues or isn't fully installed
                                    continue

                                log_message(f"  - Current bitrate: {current_br_kbps:.2f} kbps (Target: {video_bitrate_target} kbps)")
                                if current_br_kbps == 0 or current_br_kbps > (video_bitrate_target * 1.1):
                                    if not exiftool_found:
                                        log_message(f"  Skipping metadata copy for '{filename}' if compression succeeds, ExifTool not found.")
                                    process_video_file(input_path, output_path, video_bitrate_target, audio_bitrate_target)
                                    file_processed_successfully = True
                                else:
                                    log_message(f"  - Skipping compression for '{filename}': Bitrate OK.")
                                    log_message(f"  - Moving file '{filename}' to output directory without compression.")
                                    try:
                                        os.rename(input_path, output_path)
                                        file_processed_successfully = True
                                    except OSError as e:
                                        log_message(f"  - Error moving file '{input_path}' to '{output_path}': {e}")
                            
                            elif lower_filename.endswith((".jpg", ".jpeg")):
                                log_message(f"Found image: '{filename}'")
                                if not ffmpeg_found :
                                     log_message(f"  Skipping image '{filename}', ffmpeg not found.")
                                     continue
                                if not exiftool_found:
                                     log_message(f"  Skipping metadata copy for '{filename}' if compression succeeds, ExifTool not found.")
                                process_image_file(input_path, output_path, image_quality_cfg)
                                file_processed_successfully = True

                            if file_processed_successfully:
                                files_processed_this_cycle += 1

                        except FileNotFoundError as tool_fnf_error:
                            # This primarily catches if ffmpeg/exiftool is not found during their direct calls
                            # The get_video_bitrate has its own FileNotFoundError for ffprobe
                            tool_name = "Unknown tool"
                            if "ffmpeg" in str(tool_fnf_error).lower() or (hasattr(tool_fnf_error, 'filename') and "ffmpeg" in tool_fnf_error.filename):
                                tool_name = "ffmpeg"
                                ffmpeg_found = False
                            elif "exiftool" in str(tool_fnf_error).lower() or (hasattr(tool_fnf_error, 'filename') and "exiftool" in tool_fnf_error.filename):
                                tool_name = "exiftool"
                                exiftool_found = False
                            log_message(f"Error: '{tool_name}' command not found during processing of '{filename}'. Ensure it's installed and in PATH.")
                        except Exception as e_file_proc:
                            log_message(f"An error occurred processing '{filename}'. It was not removed. Error: {e_file_proc}")
                            log_message(traceback.format_exc())


                if files_processed_this_cycle > 0:
                    log_message(f"Finished processing cycle. {files_processed_this_cycle} file(s) processed.")
                else:
                    log_message("No new files to process in allowed directories during this cycle.")
            else:
                log_message(f"Current time is outside the allowed window ({time_from_cfg:.2f} - {time_to_cfg:.2f}). Waiting...")

            log_message(f"Sleeping for {sleep_duration_cfg} seconds...")
            time.sleep(sleep_duration_cfg)

        except KeyboardInterrupt:
            log_message("\nScript interrupted by user. Exiting.")
            break
        except Exception as e_main_loop:
            log_message(f"\n--- UNEXPECTED ERROR IN MAIN SCRIPT LOOP ---")
            log_message(f"Error: {e_main_loop}")
            log_message("Traceback:")
            log_message(traceback.format_exc()) # Log the full traceback
            log_message("-------------------------------------")
            log_message(f"Continuing loop after {DEFAULT_SLEEP_DURATION} seconds emergency sleep...")
            time.sleep(DEFAULT_SLEEP_DURATION)