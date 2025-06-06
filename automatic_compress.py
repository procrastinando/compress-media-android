import subprocess
import os
import re
import time
from datetime import datetime
import traceback

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
DEFAULT_SLEEP_DURATION = 300

# --- Status constants for file processing ---
STATUS_COMPLETED = "Completed"
STATUS_MOVED = "Skipped (Moved)"
STATUS_FAILED = "Failed"
STATUS_SKIPPED_EXISTS = "Skipped (Exists)" # If output already exists

def setup_logging(script_dir):
    global LOG_FILE_PATH
    LOG_FILE_PATH = os.path.join(script_dir, "logs.txt")
    log_message(f"Logging initialized. Log file: {LOG_FILE_PATH}")

def log_message(message):
    global LOG_FILE_PATH
    if not LOG_FILE_PATH:
        print(f"ERROR: LOG_FILE_PATH not set. Message: {message}")
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{now_str}] {message}\n"
    try:
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception:
        # Minimal fallback if logging itself fails
        if not hasattr(log_message, "logging_error_reported"):
            print(f"CRITICAL LOGGING ERROR: Could not write to {LOG_FILE_PATH}. Further logs lost.", file=os.sys.stderr)
            log_message.logging_error_reported = True
        pass

def read_config_yaml(config_path):
    config = {}
    reading_input_dirs = False
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("input_dir:"):
                    config["input_dir"] = []
                    reading_input_dirs = True
                    continue
                if reading_input_dirs:
                    if line.startswith("- "):
                        item = line[1:].strip()
                        if item: config["input_dir"].append(item)
                        continue
                    else:
                        reading_input_dirs = False
                if ":" in line:
                    key, value = line.split(":", 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        log_message(f"Info: Config file '{config_path}' not found. Using default values.")
        return {}
    except Exception as e:
        log_message(f"Error reading config '{config_path}': {e}. Using default values.")
        return {}
    return config

def safe_int(value, default):
    try: return int(value)
    except: return default

def safe_float(value, default):
    try: return float(value)
    except: return default

def get_video_bitrate(file_path):
    """Returns bitrate in kbps, 0 if not found/error, -1 if ffprobe missing."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore'
        )
        bitrate_str = result.stdout.strip()
        if bitrate_str == "N/A" or not bitrate_str: return 0
        return int(bitrate_str) / 1000
    except ValueError: return 0 # Non-numeric bitrate
    except subprocess.CalledProcessError: # ffprobe failed (e.g. not video)
        return 0
    except FileNotFoundError:
        log_message(f"Error: 'ffprobe' (part of FFmpeg) not found. Cannot determine video bitrates.")
        return -1 # Critical: tool missing
    except Exception:
        return 0 # Other unexpected errors

def _run_command(command_list, operation_name, filename):
    """Helper to run subprocess and handle common errors, returns True on success."""
    try:
        # We don't log stdout/stderr here to keep logs clean
        subprocess.run(command_list, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return True
    except subprocess.CalledProcessError as e:
        # Log a concise error message
        error_detail = e.stderr.strip().splitlines()[-1] if e.stderr and e.stderr.strip() else "No error detail"
        log_message(f"  Debug: {operation_name} for '{filename}' failed. CMD: {' '.join(command_list)}. Error: {error_detail}")
        return False
    except FileNotFoundError:
        tool_name = command_list[0]
        log_message(f"Error: Command '{tool_name}' not found. Please ensure it's installed and in PATH.")
        # Mark tool as globally missing if not already done
        if tool_name == "ffmpeg" and not hasattr(_run_command, "ffmpeg_missing_reported"):
            _run_command.ffmpeg_missing_reported = True
        elif tool_name == "exiftool" and not hasattr(_run_command, "exiftool_missing_reported"):
            _run_command.exiftool_missing_reported = True
        return False
    except Exception as e:
        log_message(f"  Debug: Unexpected error during {operation_name} for '{filename}': {e}")
        return False


def process_video_file(input_file, output_file, video_b_cfg, audio_b_cfg, current_bitrate_kbps):
    """Processes a video file. Returns (STATUS_STRING, error_message_or_None)."""
    filename = os.path.basename(input_file)

    # Condition to compress: unknown bitrate (0) or significantly higher than target
    should_compress = current_bitrate_kbps == 0 or current_bitrate_kbps > (video_b_cfg * 1.1)

    if should_compress:
        # Compress video
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-map_metadata", "0", "-movflags", "+use_metadata_tags",
            "-c:v", "libx265", "-b:v", f"{video_b_cfg}k",
            "-c:a", "aac", "-b:a", f"{audio_b_cfg}k",
            "-tag:v", "hvc1", output_file
        ]
        if not _run_command(ffmpeg_cmd, "Video compression", filename):
            if os.path.exists(output_file): os.remove(output_file) # Cleanup partial
            return STATUS_FAILED, "Compression error"

        # Copy metadata
        exiftool_cmd = [
            "exiftool", "-m", "-TagsFromFile", input_file,
            "-all:all>all:all", "-unsafe", "-overwrite_original", output_file
        ]
        if not _run_command(exiftool_cmd, "Metadata copy (video)", filename):
            # Compression succeeded, but metadata failed.
            # Decide: keep compressed file without full metadata, or count as full fail?
            # For now, let's count it as a fail and remove the output.
            # If you want to keep it, change status and don't remove.
            if os.path.exists(output_file): os.remove(output_file)
            return STATUS_FAILED, "Metadata copy error"

        # If all successful, remove original
        try:
            os.remove(input_file)
            return STATUS_COMPLETED, None
        except OSError as e:
            return STATUS_FAILED, f"Error removing original: {e}" # Compressed, but original not removed

    else: # Bitrate is fine, just move the file
        try:
            os.rename(input_file, output_file)
            return STATUS_MOVED, None
        except OSError as e:
            return STATUS_FAILED, f"Error moving file: {e}"


def process_image_file(input_file, output_file, quality_cfg):
    """Processes an image file. Returns (STATUS_STRING, error_message_or_None)."""
    filename = os.path.basename(input_file)
    base, ext = os.path.splitext(output_file)
    temp_output_image = f"{base}_temp_{os.getpid()}{ext}"

    # Compress image to temp file
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-q:v", str(quality_cfg), "-f", "image2", temp_output_image
    ]
    if not _run_command(ffmpeg_cmd, "Image compression", filename):
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, "Compression error"

    # Copy metadata to temp file
    exiftool_cmd = [
        "exiftool", "-m", "-TagsFromFile", input_file,
        "-all:all>all:all", "-unsafe", "-overwrite_original", temp_output_image
    ]
    if not _run_command(exiftool_cmd, "Metadata copy (image)", filename):
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, "Metadata copy error"

    # Move temp file to final output
    try:
        os.replace(temp_output_image, output_file)
    except OSError as e:
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, f"Error finalizing image: {e}"

    # If all successful, remove original
    try:
        os.remove(input_file)
        return STATUS_COMPLETED, None
    except OSError as e:
        return STATUS_FAILED, f"Error removing original: {e}" # Compressed, but original not removed
    finally: # Ensure temp is cleaned up even if os.replace or os.remove fails after it
        if os.path.exists(temp_output_image):
            try: os.remove(temp_output_image)
            except OSError: pass


if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    setup_logging(SCRIPT_DIR)
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")

    log_message("Script started.")

    # Reset missing tool flags at start of each main loop iteration for re-check
    # These are used by _run_command to avoid spamming "tool not found"
    _run_command.ffmpeg_missing_reported = False
    _run_command.exiftool_missing_reported = False
    ffprobe_globally_missing = False # Specific for bitrate check

    while True:
        try:
            # --- Read Config ---
            raw_config = read_config_yaml(CONFIG_PATH)
            input_dirs_cfg = raw_config.get("input_dir", DEFAULT_INPUT_DIRS)
            if not isinstance(input_dirs_cfg, list) or not input_dirs_cfg:
                input_dirs_cfg = DEFAULT_INPUT_DIRS
            output_dir_cfg = raw_config.get("output_dir", DEFAULT_OUTPUT_DIR)
            video_b_cfg = safe_int(raw_config.get("video_bitrate"), DEFAULT_VIDEO_BITRATE)
            audio_b_cfg = safe_int(raw_config.get("audio_bitrate"), DEFAULT_AUDIO_BITRATE)
            image_q_cfg = safe_int(raw_config.get("quality"), DEFAULT_IMAGE_QUALITY)
            time_from_cfg = safe_float(raw_config.get("time_from"), DEFAULT_TIME_FROM)
            time_to_cfg = safe_float(raw_config.get("time_to"), DEFAULT_TIME_TO)
            sleep_duration_cfg = safe_int(raw_config.get("sleep_duration"), DEFAULT_SLEEP_DURATION)

            # --- Check Time Window ---
            now = datetime.now()
            current_hour_float = now.hour + now.minute / 60.0
            is_time_allowed = (time_from_cfg <= current_hour_float < time_to_cfg) if time_from_cfg < time_to_cfg \
                              else (current_hour_float >= time_from_cfg or current_hour_float < time_to_cfg)

            if not is_time_allowed:
                log_message(f"Outside allowed processing window ({time_from_cfg:.2f} - {time_to_cfg:.2f}). Sleeping...")
                time.sleep(sleep_duration_cfg)
                continue # Skip to next iteration of the while True loop

            # --- Processing Logic (Only if within time window) ---
            log_message(f"Within processing window. Scanning for files...")

            # Create output directory if it doesn't exist
            try:
                os.makedirs(output_dir_cfg, exist_ok=True)
            except OSError as e:
                log_message(f"CRITICAL: Could not create output directory '{output_dir_cfg}': {e}. Skipping cycle.")
                time.sleep(sleep_duration_cfg)
                continue

            files_to_process = []
            for current_input_dir in input_dirs_cfg:
                if not os.path.isdir(current_input_dir):
                    log_message(f"Warning: Input directory '{current_input_dir}' not found. Skipping.")
                    continue
                try:
                    for filename in os.listdir(current_input_dir):
                        if filename.startswith("."): continue # Skip hidden
                        input_path = os.path.join(current_input_dir, filename)
                        if os.path.isfile(input_path):
                            files_to_process.append(input_path)
                except OSError as e:
                    log_message(f"Error listing files in '{current_input_dir}': {e}")

            if not files_to_process:
                log_message("No files found to process in input directories.")
            else:
                log_message(f"Found {len(files_to_process)} files to process.")
                
                processed_count = 0
                for i, input_path in enumerate(files_to_process):
                    filename = os.path.basename(input_path)
                    output_path = os.path.join(output_dir_cfg, filename)
                    log_prefix = f"{i+1}/{len(files_to_process)}: '{filename}' ->"

                    if os.path.exists(output_path):
                        log_message(f"{log_prefix} {STATUS_SKIPPED_EXISTS}")
                        # If output exists, we need to decide: remove original or leave it?
                        # To ensure input dirs are emptied, let's remove original if output exists.
                        try:
                            os.remove(input_path)
                            log_message(f"  Removed original '{filename}' as output already exists.")
                        except OSError as e:
                            log_message(f"  Warning: Could not remove original '{filename}' (output exists): {e}")
                        processed_count +=1
                        continue

                    status = STATUS_FAILED # Default status
                    error_msg = "Unknown processing error"
                    lower_filename = filename.lower()

                    try:
                        if lower_filename.endswith(".mp4"):
                            if ffprobe_globally_missing:
                                status, error_msg = STATUS_FAILED, "ffprobe missing"
                            else:
                                current_br_kbps = get_video_bitrate(input_path)
                                if current_br_kbps == -1: # ffprobe tool missing
                                    ffprobe_globally_missing = True
                                    status, error_msg = STATUS_FAILED, "ffprobe missing"
                                elif hasattr(_run_command, "ffmpeg_missing_reported") and _run_command.ffmpeg_missing_reported:
                                    status, error_msg = STATUS_FAILED, "ffmpeg missing"
                                elif hasattr(_run_command, "exiftool_missing_reported") and _run_command.exiftool_missing_reported:
                                    status, error_msg = STATUS_FAILED, "exiftool missing"
                                else:
                                    status, error_msg = process_video_file(input_path, output_path, video_b_cfg, audio_b_cfg, current_br_kbps)

                        elif lower_filename.endswith((".jpg", ".jpeg")):
                            if hasattr(_run_command, "ffmpeg_missing_reported") and _run_command.ffmpeg_missing_reported:
                                 status, error_msg = STATUS_FAILED, "ffmpeg missing"
                            elif hasattr(_run_command, "exiftool_missing_reported") and _run_command.exiftool_missing_reported:
                                status, error_msg = STATUS_FAILED, "exiftool missing"
                            else:
                                status, error_msg = process_image_file(input_path, output_path, image_q_cfg)
                        else:
                            status = "Skipped (Unsupported type)"
                            error_msg = None
                            # To empty input dirs, move unsupported files too
                            try:
                                os.rename(input_path, os.path.join(output_dir_cfg, filename))
                                log_message(f"{log_prefix} {status} (Moved to output)")
                            except OSError as e:
                                log_message(f"{log_prefix} {status} (Move failed: {e})")
                            processed_count +=1
                            continue # Go to next file

                        # Log final status for this file
                        if error_msg:
                            log_message(f"{log_prefix} {status} (Reason: {error_msg})")
                        else:
                            log_message(f"{log_prefix} {status}")
                        
                        if status != STATUS_FAILED:
                            processed_count +=1

                    except Exception as e_proc: # Catch-all for unexpected issues in file processing logic
                        log_message(f"{log_prefix} {STATUS_FAILED} (Unexpected error: {e_proc})")
                        log_message(traceback.format_exc()) # Log traceback for these unexpected ones

                log_message(f"Processing cycle finished. {processed_count} out of {len(files_to_process)} files were actioned (completed, moved, or skipped).")

            # Reset tool missing flags for next cycle, in case user installs them while script runs
            _run_command.ffmpeg_missing_reported = False
            _run_command.exiftool_missing_reported = False
            ffprobe_globally_missing = False

            log_message(f"Sleeping for {sleep_duration_cfg} seconds...")
            time.sleep(sleep_duration_cfg)

        except KeyboardInterrupt:
            log_message("Script interrupted by user. Exiting.")
            break
        except Exception as e_main:
            log_message(f"--- UNEXPECTED CRITICAL ERROR IN MAIN LOOP ---")
            log_message(f"Error: {e_main}")
            log_message(traceback.format_exc())
            log_message(f"Sleeping for {DEFAULT_SLEEP_DURATION}s before retrying.")
            time.sleep(DEFAULT_SLEEP_DURATION)