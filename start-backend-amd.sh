#!/usr/bin/env bash
#
# start-backend.sh
#
# Usage: ./start-backend.sh <TAG>
#   where <TAG> is “latest”, “v1.0”, “v2.0”, or “dev” (the local‐only build).
#

TAG="$1"
if [ -z "$TAG" ]; then
  echo "Usage: $0 <tag>   (e.g. latest, v1.0, v2, dev)"
  exit 1
fi

# 1) Pick up your Mac’s local IP so the QR code will point to the right address
export HOST_IP=$(ipconfig getifaddr en0)

# 2) Tear down any running stack
docker compose down


#
# 3) Only “pull” from Docker Hub if we’re not using the local‐only dev image.
#    If TAG == “dev”, we assume you already built or tagged that image locally.
#
if [ "$TAG" != "dev" ]; then
  echo "--- Pulling lancel00zz/facilitator-timer-app:$TAG from DockerHub..."
  docker pull --platform linux/amd64 lancel00zz/facilitator-timer-app:$TAG
fi

export TAG

# 4) Launch “docker compose” with the chosen TAG
#    (Compose looks in docker-compose.yml by default, which must reference “image: lancel00zz/facilitator-timer-app:$TAG”)
docker compose up -d