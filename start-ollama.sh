#!/bin/bash
set -euo pipefail

echo "Starting Ollama server..."
ollama serve &

echo "Waiting for Ollama to be ready (max 60 seconds)..."
for i in {1..60}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "Ollama is ready!"
        break
    fi
    sleep 1
done

echo "Pulling tinyllama..."
ollama pull tinyllama

echo "Creating custom model 'paper-analyzer'..."
ollama create paper-analyzer -f /root/.ollama/Modelfile

echo "Verifying model creation..."
ollama list

echo "AI model ready on port 11434"
echo "Models available:"
ollama list

echo "Keeping container alive..."
# Keep the container running
tail -f /dev/null
