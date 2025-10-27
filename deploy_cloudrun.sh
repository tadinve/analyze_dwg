#!/bin/bash
# Deploy both FastAPI VLM API and Streamlit UI to Google Cloud Run
# Usage: ./deploy_cloudrun.sh <OPENAI_API_KEY>

set -e

PROJECT_ID="p3-search"
REGION="us-central1"
VLM_API_IMAGE="gcr.io/$PROJECT_ID/vlm-api"
VLM_UI_IMAGE="gcr.io/$PROJECT_ID/vlm-ui"
OPENAI_API_KEY="$1"

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Usage: $0 <OPENAI_API_KEY>"
  exit 1
fi

echo "Building VLM API Docker image..."
docker buildx build --platform linux/amd64 -t $VLM_API_IMAGE ./vlm_api

echo "Building VLM UI Docker image..."
docker buildx build --platform linux/amd64 -t $VLM_UI_IMAGE ./vlm_ui

echo "Authenticating Docker with Google Cloud..."
gcloud auth configure-docker

echo "Pushing VLM API image to Google Container Registry..."
docker push $VLM_API_IMAGE

echo "Pushing VLM UI image to Google Container Registry..."
docker push $VLM_UI_IMAGE

echo "Deploying VLM API to Cloud Run..."
gcloud run deploy vlm-api \
  --image $VLM_API_IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --timeout 600 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80 \
  --cpu-throttling \
  --project $PROJECT_ID

VLM_API_URL=$(gcloud run services describe vlm-api --platform managed --region $REGION --project $PROJECT_ID --format 'value(status.url)')

echo "Deploying VLM UI to Cloud Run..."
gcloud run deploy vlm-ui \
  --image $VLM_UI_IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars VLM_API_URL=$VLM_API_URL/describe-image/ \
  --timeout 600 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80 \
  --cpu-throttling \
  --project $PROJECT_ID

echo "Deployment complete!"
echo "VLM UI URL: $(gcloud run services describe vlm-ui --platform managed --region $REGION --project $PROJECT_ID --format 'value(status.url)')"
