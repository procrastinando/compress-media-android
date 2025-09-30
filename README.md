<!-- # Compress Media Android
Compress Media Android is a simple solution to help you save storage on your phone by automatically compressing your videos and photos. Smaller file sizes make it easier and faster to upload your files to a cloud provider.

### 1. Requirements
* Android device (no root required)
### 2. Set up Termux
* If you have termux installed, uninstall it.
* Install Termux:boot https://f-droid.org/en/packages/com.termux.boot/
* Install Termux https://f-droid.org/en/packages/com.termux/
* **Give storage access to termux**
### 3. Install/update the script
Open Termux and run the following command:
```
curl -L https://raw.githubusercontent.com/procrastinando/compress-media-android/master/install.sh | bash
```
### 4. Verifying the Script
Restart the phone, To check that the compressor is running in the background, run the following command in Termux:
```
pgrep -fl automatic_compress.py
```
You can set your own configuration running the command `nano ~/compress-media-android/config.txt`, ctrl X Y to save, every modification requires the phone to restart.
### 5. Troubleshooting
If you get an error during the installation, run this command: `dpkg --configure -a` select `N` and try again. -->

# Compress Media Android

Compress Media Android is a simple solution to help you save storage on your phone by automatically compressing your videos and photos. Smaller file sizes also make it faster to upload your files to a cloud provider.

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
*   `video_bitrate`: The target bitrate for video files.
*   `audio_bitrate`: The target bitrate for audio in videos.
*   `quality`: The compression quality for images (JPEG).
*   `time_from` / `time_to`: The time window during which the script is allowed to run.
*   `sleep_duration`: How long the script waits between checking for files.
*   `delete_original`: Set to `yes` to delete original files after processing, or `no` to keep them.
*   `two_pass_encoding`: Set to `yes` for higher quality video compression at the cost of much longer processing time and battery usage.

## 5. Verifying and Monitoring
*   **After rebooting**, you can check that the compressor is running in the background with this command in Termux:
    ```bash
    pgrep -fl automatic_compress.py
    ```
*   You can view the activity log to see what the script is doing:
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