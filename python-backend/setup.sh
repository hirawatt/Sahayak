#!/bin/bash
# Setup script for Horizon AI Assistant Backend - Ubuntu/Wayland

echo "Setting up Horizon AI Assistant Backend for Ubuntu..."

# Check if running on Ubuntu
if ! grep -q "ubuntu" /etc/os-release; then
    echo "Warning: This setup is optimized for Ubuntu. Continuing anyway..."
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    tesseract-ocr \
    tesseract-ocr-eng \
    xclip \
    xdotool \
    libdbus-1-dev \
    libgirepository1.0-dev \
    pkg-config \
    libcairo2-dev \
    python3-gi \
    gir1.2-gtk-3.0

# # Create virtual environment
# echo "Creating Python virtual environment..."
# python3 -m venv venv
# source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create config directory
echo "Creating config directory..."
mkdir -p ~/.horizon-ai/logs

# Set up permissions for input devices (needed for evdev)
echo "Setting up input device permissions..."
sudo usermod -a -G input $USER
echo "You may need to log out and back in for input device permissions to take effect."

# # Test GNOME Shell Screenshot API
# echo "Testing GNOME Shell Screenshot API..."
# if command -v gnome-screenshot &> /dev/null; then
#     echo "✓ GNOME Screenshot API available"
# else
#     echo "⚠ GNOME Screenshot not found - screen capture may not work"
# fi

# Test D-Bus access
echo "Testing D-Bus access..."
if python3 -c "import dbus; print('✓ D-Bus access working')" 2>/dev/null; then
    echo "✓ D-Bus Python bindings working"
else
    echo "⚠ D-Bus Python bindings may need additional setup"
fi

echo ""
echo "Setup complete! To start the backend server:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the server: python main.py"
echo ""
echo "The backend will be available at http://localhost:8000"
echo "API documentation will be at http://localhost:8000/docs"