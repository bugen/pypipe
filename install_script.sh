#!/bin/bash

script_name="pypipe.py"
install_dir="/usr/local/bin"
symlink_name="ppp"

cp "$script_name" "$install_dir"
chmod +x "$install_dir/$script_name"

# Create a symbolic link (optional)
ln -s "$install_dir/$script_name" "$install_dir/$symlink_name"

# Update PATH (add this line to ~/.bashrc or ~/.bash_profile)
export PATH="$PATH:$install_dir" >> ~/.bashrc

echo "Installation complete. You can now run '$symlink_name' from the command line."

