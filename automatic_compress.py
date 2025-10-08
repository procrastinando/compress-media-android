import subprocess
import os
import re
import time
import shutil
import glob
from datetime import datetime
import traceback

# --- Global Log File Path ---
LOG_FILE_PATH = ""

# --- Default configuration values ---
DEFAULT_INPUT_DIRS = ["/storage/emulated/0/DCIM/Camera"]
DEFAULT_OUTPUT_DIR = "/storage/emulated/0/DCIM/Compressed"
DEFAULT_VIDEO_BITRATE = 3000
DEFAULT_AUDIO_BITRATE = 192
DEFAULT_JPG_QUALITY = 7     # For JPG (lower is better, 2-31)
DEFAULT_AVIF_QUALITY = 30    # For AVIF (higher is worse, 0-63)
DEFAULT_IMAGE_FORMAT = "jpg" # Options: jpg, avif
DEFAULT_AUDIO_CODEC = "aac"  # Options: aac, opus
DEFAULT_VIDEO_CODEC = "h265" # Options: h265, av1
DEFAULT_TIME_FROM = 23.5
DEFAULT_TIME_TO = 7.25
DEFAULT_SLEEP_DURATION = 300
DEFAULT_DELETE_ORIGINAL = "yes"
DEFAULT_TWO_PASS_ENCODING = "yes"

# --- Status constants for file processing ---
STATUS_COMPLETED = "Completed"
STATUS_MOVED = "Skipped (Moved)"
STATUS_COPIED = "Skipped (Copied)"
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
    except ValueError: return 0
    except subprocess.CalledProcessError: return 0
    except FileNotFoundError:
        log_message(f"Error: 'ffprobe' (part of FFmpeg) not found. Cannot determine video bitrates.")
        return -1
    except Exception: return 0

def _run_command(command_list, operation_name, filename):
    """Helper to run subprocess and handle common errors, returns True on success."""
    try:
        subprocess.run(command_list, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return True
    except subprocess.CalledProcessError as e:
        error_detail = e.stderr.strip().splitlines()[-1] if e.stderr and e.stderr.strip() else "No error detail"
        log_message(f"  Debug: {operation_name} for '{filename}' failed. CMD: {' '.join(command_list)}. Error: {error_detail}")
        return False
    except FileNotFoundError:
        tool_name = command_list[0]
        log_message(f"Error: Command '{tool_name}' not found. Please ensure it's installed and in PATH.")
        if tool_name == "ffmpeg" and not hasattr(_run_command, "ffmpeg_missing_reported"):
            _run_command.ffmpeg_missing_reported = True
        elif tool_name == "exiftool" and not hasattr(_run_command, "exiftool_missing_reported"):
            _run_command.exiftool_missing_reported = True
        return False
    except Exception as e:
        log_message(f"  Debug: Unexpected error during {operation_name} for '{filename}': {e}")
        return False

def cleanup_pass_logs():
    for log_file in glob.glob("ffmpeg2pass-*.log") + glob.glob("ffmpeg2pass-*.log.mbtree"):
        try:
            os.remove(log_file)
        except OSError:
            pass

def process_video_file(input_file, output_file, video_b_cfg, audio_b_cfg, current_bitrate_kbps, two_pass_cfg, delete_original_cfg, video_codec_cfg, audio_codec_cfg):
    """Processes a video file using the specified codecs. Returns (STATUS_STRING, error_message_or_None)."""
    filename = os.path.basename(input_file)
    should_compress = current_bitrate_kbps == 0 or current_bitrate_kbps > (video_b_cfg * 1.1)

    if video_codec_cfg == "av1":
        ffmpeg_video_codec, extra_pass_args, extra_final_args = "libaom-av1", ["-cpu-used", "8"], []
    else: # Default to h265
        ffmpeg_video_codec, extra_pass_args, extra_final_args = "libx265", [], ["-tag:v", "hvc1"]
    
    ffmpeg_audio_codec = "libopus" if audio_codec_cfg == "opus" else "aac"

    if should_compress:
        try:
            if two_pass_cfg:
                pass1_cmd = ["ffmpeg", "-y", "-i", input_file, "-c:v", ffmpeg_video_codec, "-b:v", f"{video_b_cfg}k", *extra_pass_args, "-pass", "1", "-an", "-f", "null", "/dev/null"]
                if not _run_command(pass1_cmd, f"Video compression ({ffmpeg_video_codec} Pass 1)", filename):
                    return STATUS_FAILED, "Compression error (Pass 1)"

                pass2_cmd = ["ffmpeg", "-i", input_file, "-map_metadata", "0", "-movflags", "+use_metadata_tags", "-c:v", ffmpeg_video_codec, "-b:v", f"{video_b_cfg}k", *extra_pass_args, "-pass", "2", "-c:a", ffmpeg_audio_codec, "-b:a", f"{audio_b_cfg}k", *extra_final_args, output_file]
                if not _run_command(pass2_cmd, f"Video compression ({ffmpeg_video_codec} Pass 2)", filename):
                    if os.path.exists(output_file): os.remove(output_file)
                    return STATUS_FAILED, "Compression error (Pass 2)"
            else:
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_file, "-map_metadata", "0", "-movflags", "+use_metadata_tags", "-c:v", ffmpeg_video_codec, "-b:v", f"{video_b_cfg}k", *extra_pass_args, "-c:a", ffmpeg_audio_codec, "-b:a", f"{audio_b_cfg}k", *extra_final_args, output_file]
                if not _run_command(ffmpeg_cmd, f"Video compression ({ffmpeg_video_codec})", filename):
                    if os.path.exists(output_file): os.remove(output_file)
                    return STATUS_FAILED, "Compression error"
        finally:
            cleanup_pass_logs()

        exiftool_cmd = ["exiftool", "-m", "-TagsFromFile", input_file, "-all:all>all:all", "-unsafe", "-overwrite_original", output_file]
        if not _run_command(exiftool_cmd, "Metadata copy (video)", filename):
            if os.path.exists(output_file): os.remove(output_file)
            return STATUS_FAILED, "Metadata copy error"

        if delete_original_cfg:
            try:
                os.remove(input_file)
            except OSError as e:
                return STATUS_FAILED, f"Error removing original: {e}"
        
        return STATUS_COMPLETED, None
    else: # Bitrate is fine, just move or copy the file
        try:
            if delete_original_cfg:
                os.rename(input_file, output_file)
                return STATUS_MOVED, None
            else:
                shutil.copy2(input_file, output_file)
                return STATUS_COPIED, None
        except (OSError, shutil.Error) as e:
            return STATUS_FAILED, f"Error moving/copying file: {e}"

def process_image_file(input_file, output_file, quality_cfg, delete_original_cfg, image_format_cfg):
    """Processes an image file. Returns (STATUS_STRING, error_message_or_None)."""
    filename = os.path.basename(input_file)
    base, ext = os.path.splitext(output_file)
    temp_output_image = f"{base}_temp_{os.getpid()}{ext}"

    if image_format_cfg == "avif":
        # Removed -noautorotate to let FFmpeg handle orientation correctly
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_file, "-c:v", "libaom-av1", "-crf", str(quality_cfg), "-cpu-used", "4", temp_output_image]
    else: # Default to JPG
        # Removed -noautorotate to let FFmpeg handle orientation correctly
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_file, "-q:v", str(quality_cfg), "-f", "image2", temp_output_image]

    if not _run_command(ffmpeg_cmd, f"Image compression ({image_format_cfg})", filename):
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, "Compression error"

    # Copy metadata but exclude orientation tag since FFmpeg already rotated the image
    exiftool_cmd = ["exiftool", "-m", "-TagsFromFile", input_file, "-all:all>all:all", "--Orientation", "-unsafe", "-overwrite_original", temp_output_image]
    if not _run_command(exiftool_cmd, "Metadata copy (image)", filename):
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, "Metadata copy error"

    # Set orientation to normal (1) since the image is now physically rotated correctly
    reset_orientation_cmd = ["exiftool", "-Orientation=1", "-n", "-overwrite_original", temp_output_image]
    if not _run_command(reset_orientation_cmd, "Reset orientation tag", filename):
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, "Orientation reset error"

    try:
        os.replace(temp_output_image, output_file)
    except OSError as e:
        if os.path.exists(temp_output_image): os.remove(temp_output_image)
        return STATUS_FAILED, f"Error finalizing image: {e}"

    if delete_original_cfg:
        try:
            os.remove(input_file)
        except OSError as e:
            return STATUS_FAILED, f"Error removing original: {e}"
    
    return STATUS_COMPLETED, None

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    setup_logging(SCRIPT_DIR)
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")

    log_message("Script started.")
    
    while True:
        try:
            _run_command.ffmpeg_missing_reported = False
            _run_command.exiftool_missing_reported = False
            ffprobe_globally_missing = False

            raw_config = read_config_yaml(CONFIG_PATH)
            input_dirs_cfg = raw_config.get("input_dir", DEFAULT_INPUT_DIRS)
            if not isinstance(input_dirs_cfg, list) or not input_dirs_cfg:
                input_dirs_cfg = DEFAULT_INPUT_DIRS
            output_dir_cfg = raw_config.get("output_dir", DEFAULT_OUTPUT_DIR)
            video_b_cfg = safe_int(raw_config.get("video_bitrate"), DEFAULT_VIDEO_BITRATE)
            audio_b_cfg = safe_int(raw_config.get("audio_bitrate"), DEFAULT_AUDIO_BITRATE)
            time_from_cfg = safe_float(raw_config.get("time_from"), DEFAULT_TIME_FROM)
            time_to_cfg = safe_float(raw_config.get("time_to"), DEFAULT_TIME_TO)
            sleep_duration_cfg = safe_int(raw_config.get("sleep_duration"), DEFAULT_SLEEP_DURATION)
            delete_original_cfg = raw_config.get("delete_original", DEFAULT_DELETE_ORIGINAL).lower() == 'yes'
            two_pass_cfg = raw_config.get("two_pass_encoding", DEFAULT_TWO_PASS_ENCODING).lower() == 'yes'
            
            video_codec_cfg = raw_config.get("video_codec", DEFAULT_VIDEO_CODEC).lower()
            if video_codec_cfg not in ["h265", "av1"]: video_codec_cfg = DEFAULT_VIDEO_CODEC
            
            audio_codec_cfg = raw_config.get("audio_codec", DEFAULT_AUDIO_CODEC).lower()
            if audio_codec_cfg not in ["aac", "opus"]: audio_codec_cfg = DEFAULT_AUDIO_CODEC
            
            image_format_cfg = raw_config.get("image_format", DEFAULT_IMAGE_FORMAT).lower()
            if image_format_cfg not in ["jpg", "avif"]: image_format_cfg = DEFAULT_IMAGE_FORMAT
            
            default_q = DEFAULT_AVIF_QUALITY if image_format_cfg == 'avif' else DEFAULT_JPG_QUALITY
            image_q_cfg = safe_int(raw_config.get("quality"), default_q)

            log_message(f"Using video codec: {video_codec_cfg}, audio codec: {audio_codec_cfg}, image format: {image_format_cfg}")

            now = datetime.now()
            current_hour_float = now.hour + now.minute / 60.0
            # SYNTAX ERROR IS FIXED HERE: Removed the incorrect line break and backslash
            is_time_allowed = (time_from_cfg <= current_hour_float < time_to_cfg) if time_from_cfg < time_to_cfg else (current_hour_float >= time_from_cfg or current_hour_float < time_to_cfg)

            if not is_time_allowed:
                log_message(f"Outside allowed processing window ({time_from_cfg:.2f} - {time_to_cfg:.2f}). Sleeping...")
                time.sleep(sleep_duration_cfg)
                continue

            log_message(f"Within processing window. Scanning for files...")
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
                        if filename.startswith("."): continue
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
                    log_prefix = f"{i+1}/{len(files_to_process)}: '{filename}' ->"
                    
                    try:
                        status, error_msg = STATUS_FAILED, "Unknown processing error"
                        lower_filename = filename.lower()
                        
                        output_filename = filename
                        if lower_filename.endswith((".jpg", ".jpeg")):
                            base, _ = os.path.splitext(filename)
                            output_filename = f"{base}.{image_format_cfg}"
                        output_path = os.path.join(output_dir_cfg, output_filename)

                        if os.path.exists(output_path):
                            log_message(f"{log_prefix} {STATUS_SKIPPED_EXISTS}")
                            if delete_original_cfg:
                                try:
                                    os.remove(input_path)
                                    log_message(f"  Removed original '{filename}' as output already exists.")
                                except OSError as e:
                                    log_message(f"  Warning: Could not remove original '{filename}' (output exists): {e}")
                            processed_count += 1
                            continue

                        if lower_filename.endswith((".jpg", ".jpeg")):
                            status, error_msg = process_image_file(input_path, output_path, image_q_cfg, delete_original_cfg, image_format_cfg)

                        elif lower_filename.endswith(".mp4"):
                            if ffprobe_globally_missing:
                                status, error_msg = STATUS_FAILED, "ffprobe missing"
                            else:
                                current_br_kbps = get_video_bitrate(input_path)
                                if current_br_kbps == -1:
                                    ffprobe_globally_missing = True
                                    status, error_msg = STATUS_FAILED, "ffprobe missing"
                                else:
                                    status, error_msg = process_video_file(input_path, output_path, video_b_cfg, audio_b_cfg, current_br_kbps, two_pass_cfg, delete_original_cfg, video_codec_cfg, audio_codec_cfg)
                        
                        else:
                            try:
                                if delete_original_cfg:
                                    os.rename(input_path, output_path)
                                    status = "Moved (Unsupported type)"
                                else:
                                    shutil.copy2(input_path, output_path)
                                    status = "Copied (Unsupported type)"
                                error_msg = None
                            except (OSError, shutil.Error) as e:
                                status, error_msg = STATUS_FAILED, f"Move/Copy failed: {e}"

                        if error_msg: log_message(f"{log_prefix} {status} (Reason: {error_msg})")
                        else: log_message(f"{log_prefix} {status}")
                        
                        if status != STATUS_FAILED: processed_count +=1

                    except Exception as e_proc:
                        log_message(f"{log_prefix} {STATUS_FAILED} (Unexpected error: {e_proc})")
                        log_message(traceback.format_exc())

                log_message(f"Processing cycle finished. {processed_count} out of {len(files_to_process)} files were actioned.")

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
            time.sleep(DEFAULT_SLEEP_DURATION)```

