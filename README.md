
To save space on your Android device while backing up photos and videos to Nextcloud, you can use Termux with Python and FFmpeg to automate media compression. Here’s how to set it up:
### 1. Requirements
* Android phone (no root required)
### 2. Installation Steps
* If you have termux installed, uninstall it.
* Install Termux:boot https://f-droid.org/en/packages/com.termux.boot/
* Install Termux https://f-droid.org/en/packages/com.termux/
* **Give storage access to termux**
### 3. Install the script
Open Termux and run the following commands:
```
pkg update && pkg upgrade -y
pkg install python -y
pkg install ffmpeg -y
pkg install exiftool -y
```
Prepare the boot script:
```
mkdir -p ~/.termux/boot/
nano ~/.termux/boot/start_compressor.sh
```
Add the following content:
```
#!/data/data/com.termux/files/usr/bin/bash
python ~/automatic_compress.py
```
Run `nano ~/automatic_compress.py` and add the content of the script in this repository.

Save the file and restart the phone, it should be compressing files older than 60 minutes automatically, saving them in the "Compressed" directory and the original files will be deleted. To make sure the script is running:
```
pgrep -fl automatic_compress.py
```
