#!/data/data/com.termux/files/usr/bin/bash
# This script uninstalls the compress-media-android project.

echo "Stopping any running compressor script..."
# Use pkill to find and kill the python script by its name.
pkill -f automatic_compress.py

echo "Removing Termux:boot startup script..."
rm -f ~/.termux/boot/start_compressor.sh

echo "Removing the repository directory..."
rm -rf ~/compress-media-android

echo "--------------------------------------"
echo "Uninstallation complete."
echo "The following dependencies are NOT removed: python, ffmpeg, exiftool, git, nano."
echo "You can remove them manually with 'pkg uninstall ...' if you no longer need them."
echo "--------------------------------------"