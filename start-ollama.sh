#!/bin/bash
set -euo pipefail   # fail fast

echo "Starting Ollama server..."
ollama serve &      # background

echo "Waiting for Ollama to be ready (max 30 s)..."
timeout 30s bash -c '
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 1
done
'

echo "Pulling tinyllama..."
ollama pull tinyllama

echo "Creating custom model 'paper-analyzer'..."
ollama create paper-analyzer -f /root/.ollama/Modelfile

echo "AI model ready on port 11434"
echo "Keeping container alive..."
wait   # keep the PID of ollama serve
