# Docker Registry Secrets Configuration Guide

This guide explains how to configure GitHub Secrets required for the Docker multi-stage build workflows to push images to your Docker registry.

## Required Secrets

The following secrets must be configured in your GitHub repository for the Docker build workflows to function:

### 1. `DOCKER_REGISTRY_URL`
- **Description:** The URL of your Docker registry endpoint
- **Examples:**
  - Docker Hub: `docker.io`
  - GitHub Container Registry: `ghcr.io`
  - Private registry: `registry.example.com`
- **Required:** Yes

### 2. `DOCKER_USERNAME`
- **Description:** Username for authenticating to the Docker registry
- **Examples:**
  - Docker Hub: Your Docker Hub username
  - GitHub Container Registry: Your GitHub username
  - Private registry: Your registry username
- **Required:** Yes

### 3. `DOCKER_PASSWORD`
- **Description:** Password or authentication token for the Docker registry
- **Examples:**
  - Docker Hub: Your Docker Hub password or personal access token
  - GitHub Container Registry: A GitHub personal access token with `write:packages` scope
  - Private registry: Your registry password or token
- **Required:** Yes
- **Security Note:** Use personal access tokens instead of passwords when possible for better security

## How to Add Secrets to Your Repository

### Step 1: Navigate to Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** (top navigation bar)
3. In the left sidebar, click on **Secrets and variables** → **Actions**

### Step 2: Create Each Secret

For each required secret, follow these steps:

1. Click the **New repository secret** button
2. Enter the secret name (e.g., `DOCKER_REGISTRY_URL`)
3. Enter the secret value
4. Click **Add secret**

### Step 3: Verify Secrets Are Added

After adding all three secrets, you should see them listed in the "Repository secrets" section:
- `DOCKER_REGISTRY_URL`
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

## Registry-Specific Setup Instructions

### Docker Hub

1. **DOCKER_REGISTRY_URL:** `docker.io`
2. **DOCKER_USERNAME:** Your Docker Hub username
3. **DOCKER_PASSWORD:** 
   - Option A: Your Docker Hub password
   - Option B (Recommended): Create a personal access token:
     - Go to Docker Hub → Account Settings → Security → New Access Token
     - Give it a descriptive name (e.g., "GitHub Actions")
     - Copy the token and use it as the password

### GitHub Container Registry (GHCR)

1. **DOCKER_REGISTRY_URL:** `ghcr.io`
2. **DOCKER_USERNAME:** Your GitHub username
3. **DOCKER_PASSWORD:**
   - Create a GitHub personal access token:
     - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
     - Click **Generate new token (classic)**
     - Select scopes: `write:packages`, `read:packages`, `delete:packages`
     - Copy the token and use it as the password

### Private Docker Registry

1. **DOCKER_REGISTRY_URL:** Your registry URL (e.g., `registry.example.com`)
2. **DOCKER_USERNAME:** Your registry username
3. **DOCKER_PASSWORD:** Your registry password or authentication token

## How Secrets Are Used in Workflows

The secrets are referenced in the GitHub Actions workflows as environment variables:

```yaml
env:
  REGISTRY_URL: ${{ secrets.DOCKER_REGISTRY_URL }}
  REGISTRY_USERNAME: ${{ secrets.DOCKER_USERNAME }}
  REGISTRY_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
```

These environment variables are then used in the Docker login step:

```yaml
- name: Login to Docker registry
  uses: docker/login-action@v3
  with:
    registry: ${{ secret.REGISTRY_URL }}
    username: ${{ secret.REGISTRY_USERNAME }}
    password: ${{ secret.REGISTRY_PASSWORD }}
```

## Workflow Files Using These Secrets

The following workflow files reference these secrets:

1. **`.github/workflows/build-runtime.yml`**
   - Triggered manually via workflow dispatch
   - Builds and pushes the runtime image
   - Uses all three secrets for authentication

2. **`.github/workflows/build-app.yml`**
   - Triggered on push to main/master branches
   - Builds and pushes the application image
   - Uses all three secrets for authentication

## Troubleshooting

### Workflow Fails with "Authentication Failed"

**Cause:** Incorrect credentials or expired token

**Solution:**
1. Verify the secret values are correct
2. If using a personal access token, ensure it hasn't expired
3. Check that the token has the required scopes (for GHCR: `write:packages`)
4. Update the secret with the correct value

### Workflow Fails with "Registry Not Found"

**Cause:** Incorrect registry URL

**Solution:**
1. Verify the `DOCKER_REGISTRY_URL` is correct for your registry
2. Common values:
   - Docker Hub: `docker.io`
   - GitHub Container Registry: `ghcr.io`
   - Private registry: Check your registry documentation

### Images Not Appearing in Registry

**Cause:** Successful build but authentication issue during push

**Solution:**
1. Check workflow logs for error messages
2. Verify all three secrets are configured
3. Ensure the user account has permission to push to the registry

## Security Best Practices

1. **Use Personal Access Tokens:** Prefer tokens over passwords for better security and granular control
2. **Limit Token Scope:** Only grant the minimum required permissions (e.g., `write:packages` for GHCR)
3. **Rotate Tokens Regularly:** Periodically update tokens to reduce risk of compromise
4. **Never Commit Secrets:** Secrets should only be stored in GitHub Secrets, never in code or configuration files
5. **Review Workflow Logs:** Workflow logs may contain sensitive information; be cautious when sharing them

## Testing Your Configuration

After configuring the secrets, you can test them by:

1. **For build-runtime.yml:**
   - Go to Actions → Build Runtime Image
   - Click "Run workflow"
   - Select the branch and click "Run workflow"
   - Monitor the workflow execution

2. **For build-app.yml:**
   - Push a commit to main/master branch
   - Go to Actions and monitor the Build Application Image workflow
   - Verify the image is pushed to your registry

## Additional Resources

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Docker Hub Personal Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
