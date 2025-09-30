# #!/data/data/com.termux/files/usr/bin/bash
# # This script installs dependencies, clones the compress-media-android repository,
# # and sets up the Termux:boot startup script.

# echo "Updating packages..."
# pkg update

# echo "Installing dependencies..."
# pkg install python ffmpeg exiftool git nano -y

# echo "Cloning (or updating) the repository..."
# cd ~
# if [ -d "compress-media-android" ]; then
#     echo "Repository already exists. Pulling latest changes..."
#     cd compress-media-android
#     git pull
# else
#     git clone https://github.com/procrastinando/compress-media-android.git
#     cd compress-media-android
# fi

# echo "Setting up Termux:boot startup script..."
# BOOT_DIR=~/.termux/boot
# mkdir -p "$BOOT_DIR"
# BOOT_SCRIPT="$BOOT_DIR/start_compressor.sh"
# cat > "$BOOT_SCRIPT" << 'EOF'
# #!/data/data/com.termux/files/usr/bin/bash
# python ~/compress-media-android/automatic_compress.py
# EOF

# chmod +x "$BOOT_SCRIPT"

# echo "--------------------------------------"
# echo "Installation complete."
# echo "Please ensure that Termux and Termux:boot are installed and have the necessary permissions."
# echo "Your media compressor will run after rebooting your android."
# echo "Modify the file ~/compress-media-android/config.yaml to set your own settings."


#!/data/data/com.termux/files/usr/bin/bash
# This script installs or updates dependencies, clones/pulls the repository,
# and sets up the Termux:boot startup script.

#!/data/data/com.termux/files/usr/bin/bash
# This script installs or updates dependencies, clones/pulls the repository,
# and sets up the Termux:boot startup script.

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

echo "--------------------------------------"
echo "Installation/Update complete."
echo "The compressor will start automatically the next time you reboot your device."
echo "To modify settings, edit the file: '~/compress-media-android/config.yaml'"
echo "To uninstall, run the script: '~/compress-media-android/uninstall.sh'"
echo "--------------------------------------"