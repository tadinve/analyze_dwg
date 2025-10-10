#!/bin/bash
# Deploy Streamlit app to Google Cloud Run
# Usage: ./deploy_cloudrun.sh <OPENAI_API_KEY>

set -e

PROJECT_ID="p3-search"
IMAGE_NAME="construction-vlm-app"
REGION="us-central1"
OPENAI_API_KEY="$1"

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Usage: $0 <OPENAI_API_KEY>"
  exit 1
fi

echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .

echo "Authenticating Docker with Google Cloud..."
gcloud auth configure-docker

echo "Pushing image to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME

echo "Deploying to Cloud Run..."
gcloud run deploy $IMAGE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --project $PROJECT_ID

echo "Deployment complete!"
