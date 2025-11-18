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
You can customize the script's behavior by editing the settings file.

1.  Open the settings file in a text editor:
    ```bash
    nano ~/compress-media-android/settings.yaml
    ```
2.  Make your desired changes. The file is commented to explain each option.
3.  Save the file and exit by pressing `Ctrl+X`, then `Y`, then `Enter`.

The script will automatically apply your new settings on its next cycle (within 5 minutes). You only need to restart your phone if you want the changes to apply immediately or if you have just installed the script for the first time.

### **Configuration**

#### **Core Settings**
*   `input_dir`: Folders to scan for media.
*   `output_dir`: Where to save converted files.
*   `files`: File extensions to process (e.g., `mp4`, `jpg`).

#### **General Conversion Choices**
*   `image`: Output format (`avif` or `jpg`).
*   `video`: Video codec (`libsvtav1`, `libaom-av1`, `h265`).
*   `audio`: Audio codec (`opus` or `aac`).
*   `two_pass`: `true` for better quality at the cost of double the time.

#### **Codec Parameters (Fine-Tuning)**

**Quality & Bitrate**
*   `crf`: The main **quality** setting for video. **Lower is better.**
*   `bitrate`: Alternative to `crf`. Sets a target file size (kbps).
*   `quality`:
    *   **Images**: `jpg` (`2`-best to `31`-worst) / `avif` (`0`-best to `63`-worst).
    *   **AAC Audio**: VBR quality (`~0.1` to `2`). **Higher is better.**
*   `vbr` (Opus): `on` or `off` to enable Variable Bit Rate.

**Speed & Performance**
*   `preset` (h265/libsvtav1): Speed vs. compression.
    *   **h265**: `medium` to `ultrafast`.
    *   **libsvtav1**: `0` (slowest) to `13` (fastest).
*   `cpu_use` (libaom-av1): `0` (slowest/best) to `8` (fastest/worst).
*   `row` / `threads` (libaom-av1): Toggles multithreading for better CPU usage.
*   `huffman` (jpg): `optimal` for slightly smaller file size.

#### **Scheduling**
*   `start_time` / `end_time`: Active hours for the script (e.g., `22.5` to `7.25`).

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
