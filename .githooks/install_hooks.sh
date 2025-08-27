#!/bin/sh

set -e

# Get the base directory of the repository
REPO_BASE_DIR=$(git rev-parse --show-toplevel)

# Define the source and destination directories
HOOKS_DIR="$REPO_BASE_DIR/.githooks"
GIT_HOOKS_DIR="$REPO_BASE_DIR/.git/hooks"

# Check if the destination directory exists
if [ ! -d "$GIT_HOOKS_DIR" ]; then
  echo "Error: $GIT_HOOKS_DIR does not exist."
  exit 1
fi

# Copy the hooks to the .git/hooks directory
echo "Copying hooks to $GIT_HOOKS_DIR..."
cp -r "$HOOKS_DIR"/* "$GIT_HOOKS_DIR/"

if [ $? -eq 0 ]; then
  echo "Hooks installed successfully."
else
  echo "Error: Failed to copy hooks."
  exit 1
fi

# Set the proper permissions for the .git/hooks directory and the files
echo "Setting permissions for the .git/hooks directory and files..."
chmod 755 "$GIT_HOOKS_DIR"
chmod 755 "$GIT_HOOKS_DIR"/*

if [ $? -eq 0 ]; then
  echo "Permissions set successfully."
else
  echo "Error: Failed to set permissions."
  exit 1
fi