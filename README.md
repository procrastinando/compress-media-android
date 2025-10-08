# Compress Media Android

Compress Media Android is a powerful, automated solution to help you save storage on your phone by compressing videos and photos. It runs in the background, monitoring folders for new media and processing them according to your rules. Smaller file sizes also make it faster to back up your files to the cloud.

## Features

*   **100% local**: No big tech involved, it is only you and your phone.
*   **Automatic Monitoring**: Runs in the background and watches your specified folders for new files.
*   **Video & Image Compression**: Intelligently compresses both videos and images to save space.
*   **Modern Codec Support**: Choose between standard codecs for compatibility (`h265`, `jpg`, `aac`) or modern codecs for superior efficiency (`av1`, `avif`, `opus`).
*   **Metadata Preservation**: Keeps all original metadata (like GPS location, date, and time) in the compressed files.
*   **Highly Configurable**: Fine-tune everything from compression quality and codecs to a daily processing schedule.

## 1. Requirements
*   Android device (no root required)
*   Termux and Termux:boot applications from F-Droid

## 2. Set up Termux
1.  If you have an old version of Termux installed (from Play Store), uninstall it.
2.  Install **Termux:boot** from F-Droid: https://f-droid.org/en/packages/com.termux.boot/
3.  Install **Termux** from F-Droid: https://f-droid.org/en/packages/com.termux/
4.  Open Termux and grant it storage access by running the command: `termux-setup-storage` and approve the request.

## 3. Install or Update the Script
Open Termux and run the following single command. It will install all necessary tools and download the script for you. If you run it again later, it will automatically update the script to the latest version.

```bash
curl -L https://raw.githubusercontent.com/procrastinando/compress-media-android/master/install-update.sh | bash
```

## 4. Configuration
You can customize the script's behavior by editing the configuration file.

1.  Open the config file in a text editor:
    ```bash
    nano ~/compress-media-android/config.yaml
    ```
2.  Make your desired changes. The file is commented to explain each option.
3.  Save the file and exit by pressing `Ctrl+X`, then `Y`, then `Enter`.

The script will automatically apply your new settings on its next cycle (within 5 minutes by default). You only need to restart your phone if you want the changes to apply immediately or if you have just installed the script for the first time.

### Configuration Options

*   `input_dir`: A list of folders to scan for new media.
*   `output_dir`: The folder where compressed files will be saved.
*   `delete_original`: Set to `yes` to delete original files after processing, or `no` to keep them.

#### Video Settings
*   `video_codec`: Choose `h265` (default, great compatibility) or `av1` (better compression but extremely slow).
*   `audio_codec`: Choose `aac` (default, best compatibility) or `opus` (more efficient, great quality at lower bitrates).
*   `video_bitrate`: The target bitrate for video files in kbps.
*   `audio_bitrate`: The target bitrate for audio. **Tip:** If using `opus`, a value of `128` is often excellent.
*   `two_pass_encoding`: Set to `yes` for potentially higher quality video at the cost of much longer processing time.

#### Image Settings
*   `image_format`: The output format for images.
    *   `jpg`: (Default) Fast and universally compatible.
    *   `avif`: Modern format. Provides files ~3 times smaller than JPG with no visible quality loss, but takes **~20 times longer** to process.
*   `quality`: Sets the compression level. **The meaning of this value depends on the `image_format` you choose!**
    *   For `jpg`: A value from `2` (best quality) to `31` (worst quality). A value of `7` is a good balance.
    *   For `avif`: A value from `0` (lossless) to `63` (worst quality). A value of `30` is a good balance.

#### Scheduling Settings
*   `time_from` / `time_to`: The time window during which the script is allowed to run (e.g., only at night).
*   `sleep_duration`: How many seconds the script waits between checking for new files.

## 5. Verifying and Monitoring
*   **After rebooting**, you can check that the compressor is running in the background with this command in Termux:
    ```bash
    pgrep -fl automatic_compress.py
    ```
*   You can view the activity log in real-time to see what the script is doing:
    ```bash
    tail -f ~/compress-media-android/logs.txt
    ```
    (Press `Ctrl+C` to stop viewing the log).

## 6. Uninstall
To completely remove the script and its startup configuration, run the provided uninstall script from your home directory:
```bash
~/compress-media-android/uninstall.sh
```

## 7. Troubleshooting
If you get an error during the installation (e.g., `dpkg` was interrupted), run this command and then try the installation command again:
```bash
dpkg --configure -a
```
