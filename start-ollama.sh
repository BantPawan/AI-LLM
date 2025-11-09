#!/bin/sh
# Start Ollama server in background
echo "🚀 Starting Ollama server..."
ollama serve &

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 10

# Pull the model
echo "📥 Downloading AI model (this takes ~30 seconds)..."
ollama pull tinyllama

# Create custom model
echo "🔧 Creating custom model..."
ollama create paper-analyzer -f /root/.ollama/Modelfile

echo "✅ AI model loaded and ready!"
echo "📊 Research Paper Analyzer is running on port 11434..."

# Keep the container alive
wait
