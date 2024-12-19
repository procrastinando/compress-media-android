
To save space on your Android device while backing up photos and videos to Nextcloud, you can use Termux with Python and FFmpeg to automate media compression. Here’s how to set it up:
### 1. Requirements
* Android phone
* Termux app installed from F-Droid.
* FFmpeg, a powerful media library for video and image processing.
* Python installed in Termux.
### 2. Installation Steps
* Install Termux: Download and install Termux from F-Droid.
* Verify Installation: Ensure both Python and FFmpeg are installed correctly:
```
python --version
ffmpeg -version
```
### 3. Install the script
Update and Install Required Packages: Open Termux and run the following commands:
```
pkg update && pkg upgrade -y
pkg install python ffmpeg -y
pkg install termux-boot -y
```
Clone the repository:
```
git clone https://github.com/procrastinando/compress-media-android
mkdir -p ~/.termux/boot/
nano ~/.termux/boot/start_compressor.sh
```
Add the following content:
```
#!/data/data/com.termux/files/usr/bin/bash
python ~/compress-media-android/automatic_compress.py
```
