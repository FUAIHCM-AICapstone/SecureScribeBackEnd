#!/bin/bash

# Fix Docker script for WSL
# This script fixes common issues with running bash scripts in WSL

echo "🔧 Fixing Docker script for WSL..."

# Check if we're in the right directory
if [ ! -f "docker-build-push.sh" ]; then
    echo "❌ docker-build-push.sh not found in current directory"
    echo "Please run this script from your project root directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo "📄 Files found:"
ls -la *.sh

# Fix line endings (convert Windows CRLF to Unix LF)
echo "🔄 Converting line endings..."
if command -v dos2unix &> /dev/null; then
    dos2unix docker-build-push.sh
    echo "✅ Line endings converted using dos2unix"
else
    # Fallback: use sed to remove carriage returns
    sed -i 's/\r$//' docker-build-push.sh
    echo "✅ Line endings converted using sed"
fi

# Make script executable
echo "🔧 Making script executable..."
chmod +x docker-build-push.sh

if [ $? -eq 0 ]; then
    echo "✅ Script is now executable"
else
    echo "❌ Failed to make script executable"
    exit 1
fi

# Verify the script
echo "🔍 Verifying script..."
ls -la docker-build-push.sh

# Test if script can be executed
if [ -x "docker-build-push.sh" ]; then
    echo "✅ Script is executable and ready to run"
    echo ""
    echo "🚀 You can now run:"
    echo "   ./docker-build-push.sh"
    echo "   ./docker-build-push.sh --tag v1.0.0"
    echo "   ./docker-build-push.sh --help"
else
    echo "❌ Script is still not executable"
    exit 1
fi

echo ""
echo "🎉 Docker script is now ready for WSL!"
echo "Run: ./docker-build-push.sh"
