import os
import time
import datetime
import subprocess
import json
import glob

LOG_FILE = "logs.txt"
SETTINGS_FILE = "settings.json"

# --- Core Helper Functions ---

def log_message(message):
    """Appends a message to the global log file AND prints to terminal."""
    print(message) 
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except OSError:
        print(f"Error: Could not write to {LOG_FILE}")

def run_command(command, verbose=False):
    """
    Runs a command.
    If verbose is True: Prints output to terminal (allows seeing FFmpeg errors).
    If verbose is False: Captures and hides output (clean mode).
    """
    try:
        if verbose:
            print(f"Running command: {' '.join(command)}")
        
        subprocess.run(
            command,
            check=True,
            # If verbose is True, we DO NOT capture output (let it flow to terminal)
            # If verbose is False, we capture output (silence it)
            capture_output=not verbose, 
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        backup_file = command[-1] + "_original"
        if os.path.exists(backup_file):
            os.remove(backup_file)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        if verbose:
            print(f"!!! COMMAND FAILED !!!")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Error details: {e.stderr}")
        return False

def get_video_duration(file_path):
    """Returns video duration in seconds using ffprobe."""
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0.0
    
def get_bitrate(file_path):
    """Returns the overall bitrate of a video file in kbps."""
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        bitrate_bps_str = result.stdout.strip()
        if bitrate_bps_str and bitrate_bps_str.lower() != 'n/a':
            return int(bitrate_bps_str) / 1000
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0
    return 0

# --- Ultimate Metadata Transfer Functions ---

def transfer_image_metadata(source_file, dest_file, verbose=False):
    # We add --ThumbnailImage and --PreviewImage to EXCLUDE them from the copy
    copy_cmd = [
        "exiftool", "-m", "-TagsFromFile", source_file,
        "-all:all", 
        "--ThumbnailImage",  # <--- ADD THIS: Do not copy the old thumbnail
        "--PreviewImage",    # <--- ADD THIS: Do not copy the old preview
        "-unsafe", "-overwrite_original", dest_file
    ]
    if not run_command(copy_cmd, verbose):
        return False

    orient_cmd = [
        "exiftool", "-m", "-Orientation=1", "-n",
        "-overwrite_original", dest_file
    ]
    if not run_command(orient_cmd, verbose):
        return False
    
    return True

def transfer_video_metadata(source_file, dest_file, verbose=False):
    copy_cmd = [
        "exiftool", "-m", "-TagsFromFile", source_file,
        "-all:all", "-unsafe", "-overwrite_original", dest_file
    ]
    return run_command(copy_cmd, verbose)

# --- Main Processing Logic ---

def process_image(file_path, settings):
    start_process_time = time.time()
    
    s_user = settings['user_settings']
    s_codecs = settings['codecs']
    is_verbose = s_user.get('verbose', False)
    
    output_dir = s_user['output_dir']
    image_format = s_user['image']
    codec_settings = s_codecs.get(image_format, {})

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.{image_format}")
    
    # Build ffmpeg command
    if image_format == 'avif':
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-c:v", "libaom-av1",
            "-crf", str(codec_settings.get('quality', 30)),
            "-cpu-used", str(codec_settings.get('cpu_use', 4)),
            output_path
        ]
    elif image_format == 'jpg':
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-q:v", str(codec_settings.get('quality', 4)),
            "-huffman", codec_settings.get('huffman', 'optimal'),
            output_path
        ]
    else:
        return 

    if run_command(cmd, is_verbose):
        if transfer_image_metadata(file_path, output_path, is_verbose):
            try:
                os.remove(file_path)
                duration = time.time() - start_process_time
                timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                log_message(f"{timestamp} > {os.path.basename(output_path)} > {duration:.2f}s")
            except OSError:
                pass 

def process_video(file_path, settings):
    start_process_time = time.time()

    s_user = settings['user_settings']
    s_codecs = settings['codecs']
    is_verbose = s_user.get('verbose', False)
    
    output_dir = s_user['output_dir']
    video_codec = s_user['video']
    audio_codec = s_user['audio']
    codec_settings = s_codecs.get(video_codec, {})
    audio_settings = s_codecs.get(audio_codec, {})

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.mp4")

    # --- BITRATE CHECK ---
    try:
        target_bitrate_str = str(codec_settings.get('bitrate', '0k'))
        target_bitrate_kbps = int(target_bitrate_str.lower().replace('k', ''))
    except (ValueError, AttributeError):
        target_bitrate_kbps = 0

    source_bitrate_kbps = get_bitrate(file_path)

    should_convert = (
        source_bitrate_kbps == 0 or 
        target_bitrate_kbps == 0 or 
        source_bitrate_kbps > (target_bitrate_kbps * 1.1)
    )

    if not should_convert:
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(file_path, output_path)
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            log_message(f"{timestamp} > {os.path.basename(file_path)} > Skipped")
        except OSError:
            pass
        return 

    # --- CONVERSION ---
    base_cmd = ["ffmpeg", "-y", "-i", file_path]
    video_opts = ["-c:v", video_codec]
    audio_opts = ["-c:a", audio_codec]
    
    if 'crf' in codec_settings: video_opts.extend(["-crf", str(codec_settings['crf'])])
    else: video_opts.extend(["-b:v", codec_settings.get('bitrate', '2500k')])
    
    if 'preset' in codec_settings: video_opts.extend(["-preset", str(codec_settings['preset'])])
    if 'cpu_use' in codec_settings: video_opts.extend(["-cpu-used", str(codec_settings['cpu_use'])])
    if codec_settings.get('row') == 1: video_opts.extend(["-row-mt", "1"])
    if 'threads' in codec_settings: video_opts.extend(["-threads", str(codec_settings['threads'])])

    if audio_codec == 'aac' and 'quality' in audio_settings:
        audio_opts.extend(["-q:a", str(audio_settings['quality'])])
    elif audio_codec == 'opus' and 'vbr' in audio_settings:
        audio_opts.extend(["-vbr", audio_settings['vbr']])
        audio_opts.extend(["-b:a", audio_settings.get('bitrate', '96k')])
    else:
        audio_opts.extend(["-b:a", audio_settings.get('bitrate', '192k')])

    success = False
    if s_user.get('two_pass', False):
        video_opts_pass2 = ["-c:v", video_codec, "-b:v", codec_settings.get('bitrate', '2500k')]
        if 'preset' in codec_settings: video_opts_pass2.extend(["-preset", str(codec_settings['preset'])])
        
        pass1_log_file = f"ffmpeg2pass-{os.getpid()}"
        pass1_cmd = base_cmd + video_opts + ["-pass", "1", "-passlogfile", pass1_log_file, "-an", "-f", "null", os.devnull]
        pass2_cmd = base_cmd + video_opts_pass2 + audio_opts + ["-pass", "2", "-passlogfile", pass1_log_file, output_path]

        success = run_command(pass1_cmd, is_verbose) and run_command(pass2_cmd, is_verbose)
        
        for log_file in glob.glob(f"{pass1_log_file}*"):
            try: os.remove(log_file)
            except OSError: pass
    else:
        cmd = base_cmd + video_opts + audio_opts + [output_path]
        success = run_command(cmd, is_verbose)

    if success:
        if transfer_video_metadata(file_path, output_path, is_verbose):
            try:
                os.remove(file_path)
                total_duration = time.time() - start_process_time
                video_length = get_video_duration(output_path)
                time_per_sec = total_duration / video_length if video_length > 0 else 0
                timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                log_message(f"{timestamp} > {os.path.basename(output_path)} > {time_per_sec:.2f}s / {total_duration:.2f}s")
            except OSError:
                pass

def is_in_schedule(start_float, end_float):
    now = datetime.datetime.now()
    current_hour_float = now.hour + now.minute / 60.0
    
    if start_float > end_float:
        return current_hour_float >= start_float or current_hour_float < end_float
    else:
        return start_float <= current_hour_float < end_float

def main():
    while True:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            s_user = settings['user_settings']
            s_sched = s_user['scheduling']
            
            if not is_in_schedule(s_sched['start_time'], s_sched['end_time']):
                time.sleep(s_sched['sleep'])
                continue

            os.makedirs(s_user['output_dir'], exist_ok=True)
            
            files_to_process = []
            allowed_exts = tuple(f".{ext}" for ext in s_user['files'])
            image_exts = ('.jpg', '.jpeg', '.heic')

            for in_dir in s_user['input_dir']:
                if os.path.isdir(in_dir):
                    for filename in os.listdir(in_dir):
                        if filename.lower().endswith(allowed_exts):
                            files_to_process.append(os.path.join(in_dir, filename))
            
            if files_to_process:
                log_message(f"<<<<< {len(files_to_process)} files found, starting conversion >>>>>")
                for file_path in files_to_process:
                    if not os.path.exists(file_path):
                        continue
                        
                    if file_path.lower().endswith(image_exts):
                        process_image(file_path, settings)
                    else:
                        process_video(file_path, settings)

            time.sleep(s_sched['sleep'])

        except FileNotFoundError:
            print(f"Waiting for {SETTINGS_FILE}...")
            time.sleep(60)
        except json.JSONDecodeError:
            log_message(f"Error: {SETTINGS_FILE} contains invalid JSON.")
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nConverter stopped by user.")
            break
        except Exception as e:
            log_message(f"Critical Error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()

