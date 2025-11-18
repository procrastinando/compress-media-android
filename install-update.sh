echo "Updating packages..."
pkg update

echo "Installing dependencies..."
pkg install python ffmpeg exiftool git nano -y

# Navigate to home directory to ensure we clone in the right place
cd ~

echo "Cloning (or updating) the repository..."
if [ -d "compress-media-android" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd compress-media-android
    git pull
else
    git clone https://github.com/procrastinando/compress-media-android.git
    cd compress-media-android
fi

echo "Setting up Termux:boot startup script..."
BOOT_DIR=~/.termux/boot
mkdir -p "$BOOT_DIR"
BOOT_SCRIPT="$BOOT_DIR/start-compressor.sh"

# Create the boot script to run the python process in the background
cat > "$BOOT_SCRIPT" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# This script starts the media compressor in the background.
# The '&' is crucial to prevent the boot process from hanging.
# Logs can be viewed in ~/compress-media-android/logs.txt
python ~/compress-media-android/automatic_compress.py &
EOF

# Set execute permission for the boot script
chmod +x "$BOOT_SCRIPT"

echo "Making uninstall script executable..."
# Set execute permission for the uninstall script
if [ -f "uninstall.sh" ]; then
    chmod +x uninstall.sh
fi
if [ -f "install-update.sh" ]; then
    chmod +x install-update.sh
fi

echo "--------------------------------------"
echo "Installation/Update complete."
echo "The compressor will start automatically the next time you reboot your device."
echo "To modify settings, edit the file: '~/compress-media-android/settings.yaml'"
echo "To uninstall, run the script: '~/compress-media-android/uninstall.sh'"
echo "--------------------------------------"
