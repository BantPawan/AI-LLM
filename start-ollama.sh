#!/bin/bash
set -euo pipefail

echo "Starting Ollama server..."
ollama serve &

echo "Waiting for Ollama to be ready (max 30 s)..."
timeout 30s bash -c '
  until nc -z localhost 11434 2>/dev/null; do
    sleep 1
  done
' || { echo "Ollama failed to start within 30 seconds"; exit 1; }

echo "Pulling tinyllama..."
ollama pull tinyllama

echo "Creating custom model 'paper-analyzer'..."
ollama create paper-analyzer -f /root/.ollama/Modelfile

echo "AI model ready on port 11434"
echo "Keeping container alive..."
wait
