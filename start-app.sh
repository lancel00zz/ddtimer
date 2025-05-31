#!/bin/bash

# Step 0: detect your Mac's Wi-Fi IP
HOST_IP=$(ipconfig getifaddr en0)

if [ -z "$HOST_IP" ]; then
  echo "❌ Could not detect IP address. Make sure you're connected to Wi-Fi."
  exit 1
fi

echo "✅ Using IP: $HOST_IP"

# Step 1: Rebuild the container with IP
HOST_IP=$HOST_IP docker-compose down
HOST_IP=$HOST_IP docker-compose up --build -d

# Step 2: Start the Electron app
echo "🚀 Launching Electron..."
cd electron
npm start