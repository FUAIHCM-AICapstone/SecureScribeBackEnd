#!/bin/bash

# Test runner script for SecureScribeBE

set -e

echo "Running unit tests..."

if [ "$1" = "docker" ]; then
    echo "Running tests with Docker..."
    docker-compose --profile test up --abort-on-container-exit test
elif [ "$1" = "local" ]; then
    echo "Running tests locally..."
    pytest tests/ -v --tb=short
else
    echo "Usage: $0 {docker|local}"
    echo "  docker: Run tests in Docker containers"
    echo "  local:  Run tests on local machine"
    exit 1
fi

echo "Tests completed successfully!"
