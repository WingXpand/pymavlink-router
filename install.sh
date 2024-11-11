#!/bin/bash

# Ensure the script exits if a command fails
set -e

# Install pymavlink
echo "Installing pymavlink..."
pip install pymavlink

DEST_DIR="$HOME/.local/bin"
SCRIPT_NAME="pymavlink-router.py"

# Ensure the destination exists
mkdir -p "$DEST_DIR"

# Copy the script to the destination
echo "Copying $SCRIPT_NAME to $DEST_DIR..."
cp "$(dirname "$BASH_SOURCE")/$SCRIPT_NAME" "$DEST_DIR"

# Make the script executable
chmod +x "$DEST_DIR/$SCRIPT_NAME"

echo "Setup complete"
