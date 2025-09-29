#!/bin/bash

echo "Setting up Brane development environment..."

# Install pnpm globally
npm install -g pnpm

# Install build essentials for native modules
sudo apt-get update
sudo apt-get install -y build-essential cmake python3-dev

# Install Ollama (optional, for testing)
curl -fsSL https://ollama.ai/install.sh | sh || true

# Create necessary directories
mkdir -p /workspace/models
mkdir -p /workspace/axon_storage
mkdir -p /workspace/logs

# Download a small test model (optional)
# You can uncomment this to download Mistral 7B Q4_0
# wget -O /workspace/models/mistral-7b-q4_0.gguf https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_0.gguf

echo "✅ Brane development environment setup complete!"
echo ""
echo "To get started:"
echo "1. Run 'pnpm install' to install dependencies"
echo "2. Run 'pnpm dev:cli' to test the CLI version"
echo "3. Run 'pnpm dev' to start the Electron app (use VNC viewer on port 6080)"
echo ""
echo "VNC Access: http://localhost:6080 (password: brane)"