# Compress Media Android
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
If you get an error during the installation, run this command: `dpkg --configure -a` select `N` and try again.
