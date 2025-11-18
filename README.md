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

---

### User Settings (`user_settings`)

| Setting | Description | Values / Range |
| :--- | :--- | :--- |
| **`input_dir`** | List of folders to scan for files. | `["/path/to/A", "/path/to/B"]` |
| **`output_dir`** | Folder where converted files are saved. | `"/path/to/output"` |
| **`files`** | File extensions to detect and process. | `["mp4", "mov", "jpg", "heic", ...]` |
| **`verbose`** | Show full FFmpeg logs in the terminal. | `true` (debug), `false` (clean logs) |
| **`image`** | Target format for image conversion. | `avif` (recommended), `jpg` |
| **`video`** | Target video encoder to use. | `libsvtav1` (fast AV1), `libaom-av1` (high qual), `libx264`, `libx265` |
| **`audio`** | Target audio encoder to use. | `libopus` (best), `aac` |
| **`two_pass`** | Enables 2-pass encoding (slower, accurate size). | `true`, `false` (recommended for CRF) |

### Scheduling
| Setting | Description | Values |
| :--- | :--- | :--- |
| `start_time` | Hour to start processing (24h format). | `0` - `24` (e.g., `22.5` is 10:30 PM) |
| `end_time` | Hour to stop processing. | `0` - `24` (e.g., `7.0` is 7:00 AM) |
| `sleep` | Wait time between folder scans (in seconds). | Integer (e.g., `60`, `300`) |

### Codec Settings (`codecs`)

#### - Video Encoders (`libsvtav1`, `libaom-av1`, `h265`, `libx264`)
| Parameter | Description | Range / Alternatives |
| :--- | :--- | :--- |
| **`crf`** | Constant Rate Factor (Quality). Lower = Better quality, larger file. | **AV1:** `20`-`40` (Rec: 25)<br>**x264/5:** `18`-`28` (Rec: 23) |
| **`preset`** | Encoding speed. Slower=Better compression. | **SVT-AV1:** `0`best - `13` worst (Rec: 8-10)<br>**x264/5:** `veryslow`, `medium`, `ultrafast` |
| **`bitrate`** | Target bitrate (ignored if CRF is used in 1-pass). | String: `"2500k"`, `"4M"` |
| **`cpu_use`** | (libaom-av1 only) CPU utilization efficiency. | `0`-`8` (Rec: 4-6) |
| **`row`** | (libaom-av1 only) Enable row-based multithreading. | `1` (on), `0` (off) |

#### - Audio Encoders (`libopus`, `aac`)
| Parameter | Description | Range / Alternatives |
| :--- | :--- | :--- |
| **`bitrate`** | Audio bitrate. | `"64k"`, `"96k"` (Opus), `"128k"`, `"192k"` (AAC) |
| **`vbr`** | (Opus) Variable Bit Rate mode. | `"on"`, `"off"`, `"constrained"` |
| **`quality`** | (AAC) VBR Quality setting. | `0.1` - `2.0` (Higher is better) |

### - Image Encoders
| Format | Parameter | Description | Range |
| :--- | :--- | :--- | :--- |
| **`avif`** | `quality` | CRF value (Inverse quality). | `20`-`40` (Lower is better) |
| | `cpu_use` | Speed setting. | `0`-`8` (Higher is faster) |
| **`jpg`** | `quality` | FFmpeg q-scale. | `2`-`31` (Lower is better, Rec: 2-5) |
| | `huffman` | Coding table strategy. | `"optimal"`, `"default"` |

---

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
