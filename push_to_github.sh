#!/bin/bash

# This script will help you push to GitHub with your PAT
# Run it manually: bash push_to_github.sh

echo "Pushing to GitHub..."
echo "When prompted for password, paste your Personal Access Token"
echo "Note: The password/token won't be visible when you type/paste it"
echo ""

git push -u origin main

echo ""
echo "If successful, you can now open the repo in GitHub Codespaces!"
echo "URL: https://github.com/SharminSirajudeen/brane_v2"