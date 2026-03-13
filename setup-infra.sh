#!/usr/bin/env bash
# Setup Google Cloud infrastructure for MedGemma Explica
# Usage: ./setup-infra.sh <PROJECT_ID> [REGION]

set -euo pipefail

PROJECT_ID="${1:?Usage: ./setup-infra.sh <PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"
BUCKET_NAME="${PROJECT_ID}-medgemma-explica"

echo "=== MedGemma Explica - Infrastructure Setup ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Bucket:  ${BUCKET_NAME}"
echo ""

# Set project
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo "--- Enabling APIs ---"
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com

# Create GCS bucket
echo "--- Creating GCS bucket ---"
if ! gsutil ls "gs://${BUCKET_NAME}" &>/dev/null; then
  gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"
  echo "Bucket created: gs://${BUCKET_NAME}"
else
  echo "Bucket already exists: gs://${BUCKET_NAME}"
fi

# Create Firestore database (Native mode)
echo "--- Setting up Firestore ---"
if ! gcloud firestore databases describe --project="${PROJECT_ID}" &>/dev/null; then
  gcloud firestore databases create \
    --location="${REGION}" \
    --type=firestore-native
  echo "Firestore database created"
else
  echo "Firestore database already exists"
fi

# Create Artifact Registry repository
echo "--- Setting up Artifact Registry ---"
AR_REPO="medgemma-explica"
if ! gcloud artifacts repositories describe "${AR_REPO}" \
    --location="${REGION}" &>/dev/null; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="MedGemma Explica container images"
  echo "Artifact Registry repo created: ${AR_REPO}"
else
  echo "Artifact Registry repo already exists: ${AR_REPO}"
fi

# Upload sample X-rays to GCS
echo "--- Uploading sample X-rays ---"
if [ -d "sample-xrays" ]; then
  gsutil -m cp -n sample-xrays/* "gs://${BUCKET_NAME}/sample-xrays/"
  echo "Sample X-rays uploaded"
else
  echo "No sample-xrays/ directory found, skipping"
fi

echo ""
echo "=== Infrastructure setup complete ==="
echo ""
echo "Next steps:"
echo "1. Deploy MedGemma 1.5 from Vertex AI Model Garden"
echo "   Visit: https://console.cloud.google.com/vertex-ai/model-garden"
echo "   Search for 'MedGemma' and deploy to an endpoint"
echo "2. If the MedGemma endpoint is in a DIFFERENT project, run:"
echo "   ./setup-cross-project-access.sh <THIS_PROJECT_ID> <ENDPOINT_PROJECT_ID>"
echo "3. Then deploy with: ./deploy.sh"
