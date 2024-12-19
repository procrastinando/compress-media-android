
To save space on your Android device while backing up photos and videos to Nextcloud, you can use Termux with Python and FFmpeg to automate media compression. Here’s how to set it up:
### 1. Requirements
* Android phone (no root required)
### 2. Installation Steps
* If you have termux installed, uninstall it.
* Install Termux:boot https://f-droid.org/en/packages/com.termux.boot/
* Install Termux https://f-droid.org/en/packages/com.termux/
### 3. Install the script
Open Termux and run the following commands:
```
pkg update && pkg upgrade -y
pkg install wget -y
pkg install python ffmpeg -y
pkg install termux-boot -y
```
Clone the repository:
```
wget https://github.com/procrastinando/compress-media-android
mkdir -p ~/.termux/boot/
nano ~/.termux/boot/start_compressor.sh
```
Add the following content:
```
#!/data/data/com.termux/files/usr/bin/bash
python ~/compress-media-android/automatic_compress.py
```
Save the file and restart the phone, it should be compressing files older than 60 minutes automatically, saving them in the "Compressed" directory and the original files will be deleted.
