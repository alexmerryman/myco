#!/bin/bash

# Build and deploy to fly.io
echo "Deploying to fly.io..."

# Install flyctl if not already installed
if ! command -v flyctl &> /dev/null; then
    echo "Installing flyctl..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

# Launch the app (first time only)
# flyctl launch

# Deploy the app
flyctl deploy

echo "Deployment complete! App should be available at: https://inat-viewer.fly.dev"