#!/bin/bash

# Get local IP address for QR routing
export HOST_IP=$(ipconfig getifaddr en0)

# Start backend container using prebuilt image
docker-compose -f docker-compose.dev.yml down
docker compose pull
docker-compose -f docker-compose.dev.yml up
