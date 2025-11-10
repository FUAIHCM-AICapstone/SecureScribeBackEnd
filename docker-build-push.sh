#!/bin/bash

# Build and push script for SecureScribe backend Docker image
# Usage: ./docker-build-push.sh [tagname]
# Default tagname is "backend" if not provided
#
# Security Note: For production use, set DOCKER_USERNAME and DOCKER_PASSWORD as environment variables:
# export DOCKER_USERNAME="luongnguyenminhan"
# export DOCKER_PASSWORD="your_password"
# Then run: ./docker-build-push.sh

set -e  # Exit on any error

# Set default tagname if not provided
TAGNAME=${1:-backend}

# Docker credentials (can also be set as environment variables)
DOCKER_USERNAME="${DOCKER_USERNAME:-luongnguyenminhan}"
DOCKER_PASSWORD="${DOCKER_PASSWORD:-Abc@12345}"

# Docker image details
DOCKER_REGISTRY="luongnguyenminhan"
IMAGE_NAME="securescribe"
FULL_IMAGE_NAME="$DOCKER_REGISTRY/$IMAGE_NAME:$TAGNAME"

echo "🐳 Building and pushing SecureScribe backend Docker image..."
echo "📝 Image: $FULL_IMAGE_NAME"
echo ""

# Login to Docker Hub
echo "🔐 Logging into Docker Hub..."
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Build the Docker image (standalone - no code mounting required)
echo "🔨 Building standalone Docker image..."
echo "📦 This image contains all application code and can run anywhere"
docker build --platform linux/amd64 -t "$FULL_IMAGE_NAME" -f Dockerfile .

# Push the image to registry
echo "⬆️  Pushing image to registry..."
docker push --platform linux/amd64 "$FULL_IMAGE_NAME"

echo ""
echo "✅ Successfully built and pushed image: $FULL_IMAGE_NAME"
echo "🎉 Deployment ready!"
