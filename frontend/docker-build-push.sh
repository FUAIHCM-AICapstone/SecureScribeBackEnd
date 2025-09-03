#!/bin/bash

# Script to build and push Docker image for meobeo-frontend
# Compatible with WSL (Windows Subsystem for Linux)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Registry information
REGISTRY="harbor.epoints.vn/ai"
REPO_NAME="frecord-frontend-mom"
TAG="latest"

# Helper function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -t, --tag TAG                   Tag for the Docker image. Default: latest"
  echo "  --no-cache                      Disable Docker build cache"
  echo "  -h, --help                      Show this help message"
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -t|--tag) TAG="$2"; shift ;;
    --no-cache) USE_CACHE="false" ;;
    -h|--help) show_usage; exit 0 ;;
    *) echo "Unknown parameter: $1"; show_usage; exit 1 ;;
  esac
  shift
done

# WSL-specific checks
check_wsl_environment() {
    print_status "Checking environment..."

    # Check if we're in WSL
    if [[ -f /proc/version ]] && grep -qi "microsoft\|wsl" /proc/version; then
        print_warning "Running in WSL environment"
        print_warning "Make sure Docker Desktop is running on Windows with WSL integration enabled"
    fi

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_error "Please install Docker Desktop and enable WSL integration"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_error "Please start Docker Desktop on Windows"
        exit 1
    fi

    print_success "Environment check passed"
}

echo "====== MeoBeo Frontend Docker Build & Push Script ======"
echo "Using tag: $TAG"
echo "Using cache: $USE_CACHE"
echo "===================================================="

# Function to build and push image
build_and_push() {
  local full_image_name="$REGISTRY/$REPO_NAME:$TAG"

  print_status "Building Docker image..."
  print_status "Image name: $full_image_name"

  # Set up cache options
  local cache_option=""
  if [ "$USE_CACHE" = "false" ]; then
    cache_option="--no-cache"
    print_warning "Build cache disabled"
  fi

  # Build the Docker image with port override
  print_status "Starting Docker build..."
  if docker build --platform linux/amd64 \
    $cache_option \
    --build-arg TZ="Asia/Ho_Chi_Minh" \
    --build-arg PORT=3000 \
    -t "$full_image_name" .; then
    print_success "Docker image built successfully: $full_image_name"
  else
    print_error "Docker build failed"
    return 1
  fi

  # Push the Docker image
  print_status "Pushing image to registry..."
  if docker push "$full_image_name"; then
    print_success "Image pushed successfully: $full_image_name"
  else
    print_error "Failed to push image to registry"
    print_error "Make sure you are logged in to the registry:"
    print_error "docker login harbor.epoints.vn"
    return 1
  fi

  return 0
}

# Perform environment checks
check_wsl_environment

# Build and push image
print_status "Starting build and push process..."
if build_and_push; then
  print_success "Build and push completed successfully!"
  echo "===================================================="
  print_success "Docker image is now available in the registry"
  print_success "Image: $REGISTRY/$REPO_NAME:$TAG"
  echo "===================================================="
else
  print_error "Build and push failed"
  exit 1
fi
