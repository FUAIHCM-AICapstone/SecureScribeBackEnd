# Docker Multi-Stage Build Setup Guide

This guide provides an overview of the Docker multi-stage build system and how to set it up for your repository.

## Overview

The Docker multi-stage build system consists of:

1. **Runtime Image** - Contains Python 3.11, system dependencies, and all Python packages
2. **Application Image** - Built on top of the runtime image, contains only application code
3. **GitHub Actions Workflows** - Automate building and pushing images to your Docker registry

## Quick Start

### 1. Configure GitHub Secrets

Before the workflows can push images, you must configure three secrets in your GitHub repository:

- `DOCKER_REGISTRY_URL` - Your Docker registry endpoint (e.g., `docker.io`, `ghcr.io`)
- `DOCKER_USERNAME` - Your registry username
- `DOCKER_PASSWORD` - Your registry password or personal access token

**See [DOCKER_SECRETS_SETUP.md](./DOCKER_SECRETS_SETUP.md) for detailed instructions.**

### 2. Build the Runtime Image

The runtime image must be built first and pushed to your registry:

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Build Runtime Image** workflow
4. Click **Run workflow**
5. Select your branch and click **Run workflow**
6. Wait for the workflow to complete

The runtime image will be tagged as:
- `{registry}/runtime:v{YYYYMMDD-HHMMSS}` (version tag)
- `{registry}/runtime:latest` (latest tag)

### 3. Push Code to Trigger Application Build

Once the runtime image is available, the application build workflow will automatically trigger on push:

1. Make changes to your code
2. Push to `main` or `master` branch
3. The **Build Application Image** workflow will automatically start
4. Wait for the workflow to complete

The application image will be tagged as:
- `{registry}/app:{commit-sha}` (commit-specific tag)
- `{registry}/app:latest` (latest tag)

## Workflow Details

### Build Runtime Image Workflow

**File:** `.github/workflows/build-runtime.yml`

**Trigger:** Manual dispatch (workflow_dispatch)

**What it does:**
1. Checks out the repository
2. Sets up Docker Buildx
3. Generates a version tag with timestamp
4. Logs in to your Docker registry
5. Builds the runtime image from `build/Dockerfile.runtime`
6. Pushes the image with version and latest tags
7. Logs out from the registry

**When to use:**
- When you update `requirements.txt` with new Python packages
- When you need to update system dependencies
- When you want to refresh the base image

### Build Application Image Workflow

**File:** `.github/workflows/build-app.yml`

**Trigger:** Push to main/master branch (excluding documentation and config files)

**What it does:**
1. Checks out the repository
2. Sets up Docker Buildx
3. Extracts the commit SHA
4. Logs in to your Docker registry
5. Builds the application image from `build/Dockerfile.app`
6. Pushes the image with commit SHA and latest tags
7. Logs out from the registry

**When it runs:**
- Automatically on every push to main/master
- Skips if only documentation or config files changed

## Dockerfile Structure

### Runtime Dockerfile

**Location:** `build/Dockerfile.runtime`

**Contains:**
- Python 3.11 base image
- System dependencies (libpango, libcairo, ffmpeg, etc.)
- Python packages from requirements.txt
- Non-root user setup
- Config directory setup

**Does NOT contain:**
- Application code

### Application Dockerfile

**Location:** `build/Dockerfile.app`

**Contains:**
- Runtime image as base
- Application code (app/, start.sh)
- Port 8000 exposure
- Startup command

**Does NOT contain:**
- System dependencies (inherited from runtime)
- Python packages (inherited from runtime)

## Local Testing

You can test the Docker builds locally without pushing to a registry:

### Build Runtime Image Locally

```bash
docker build -f build/Dockerfile.runtime -t myapp/runtime:latest .
```

### Build Application Image Locally

```bash
docker build -f build/Dockerfile.app -t myapp/app:latest .
```

### Run Application Image Locally

```bash
docker run -p 8000:8000 myapp/app:latest
```

## Image Tagging Strategy

### Runtime Image Tags

- `runtime:v{YYYYMMDD-HHMMSS}` - Timestamped version tag for reproducibility
- `runtime:latest` - Points to the most recent runtime image

### Application Image Tags

- `app:{commit-sha}` - Commit-specific tag for traceability (first 7 characters of commit SHA)
- `app:latest` - Points to the most recent application image

## Benefits of This Approach

1. **Faster Builds:** Application image builds are fast because dependencies are already in the runtime image
2. **Reproducibility:** Runtime images are versioned, allowing you to rebuild with specific dependency versions
3. **Efficient Storage:** Runtime image is built once and reused multiple times
4. **Clear Separation:** Runtime dependencies and application code are clearly separated
5. **Automated Workflow:** GitHub Actions automates the build and push process

## Troubleshooting

### Workflow Fails with Authentication Error

See [DOCKER_SECRETS_SETUP.md](./DOCKER_SECRETS_SETUP.md#troubleshooting) for troubleshooting steps.

### Application Build Fails with "Base Image Not Found"

**Cause:** Runtime image hasn't been built yet

**Solution:** Manually trigger the Build Runtime Image workflow first

### Images Not Appearing in Registry

**Cause:** Successful build but authentication issue during push

**Solution:**
1. Check workflow logs for error messages
2. Verify all secrets are configured correctly
3. Ensure your registry credentials are valid

## Next Steps

1. Configure GitHub Secrets (see [DOCKER_SECRETS_SETUP.md](./DOCKER_SECRETS_SETUP.md))
2. Manually trigger the Build Runtime Image workflow
3. Push code to main/master to trigger the application build
4. Verify images appear in your Docker registry

## Additional Resources

- [Docker Multi-Stage Builds Documentation](https://docs.docker.com/build/building/multi-stage/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
