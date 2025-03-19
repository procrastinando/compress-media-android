#!/data/data/com.termux/files/usr/bin/bash
# This script installs dependencies, clones the compress-media-android repository,
# and sets up the Termux:boot startup script.

echo "Updating packages..."
pkg update

echo "Installing dependencies..."
pkg install python ffmpeg exiftool git nano -y

echo "Cloning (or updating) the repository..."
cd ~
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
BOOT_SCRIPT="$BOOT_DIR/start_compressor.sh"
cat > "$BOOT_SCRIPT" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python ~/compress-media-android/automatic_compress.py
EOF

chmod +x "$BOOT_SCRIPT"

echo "Installation complete."
echo "Please ensure that Termux and Termux:boot are installed and have the necessary permissions."
echo "Your media compressor will run after rebooting your android."
echo "Modify the file ~/compress-media-android/config.txt to set your own settings."
