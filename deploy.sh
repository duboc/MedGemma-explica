#!/usr/bin/env bash
# Deploy MedGemma Explica to Cloud Run (single container)
#
# Usage: ./deploy.sh [REGION]
#
# Builds frontend + backend into a single container and deploys
# as one Cloud Run service. The frontend is served as static files
# by FastAPI — no CORS or VITE_API_URL needed.
#
# Prerequisites:
#   1. ./setup-infra.sh <PROJECT_ID>
#   2. If the MedGemma endpoint is in a DIFFERENT project:
#      ./setup-cross-project-access.sh <PROJECT_ID> <ENDPOINT_PROJECT_ID>
#   3. A deployed MedGemma endpoint (note the URL, project number, and ID)

set -euo pipefail

# --- Configuration ---
PROJECT_ID="riojucu"
REGION="${1:-us-central1}"
BUCKET_NAME="${PROJECT_ID}-medgemma-explica"

# MedGemma endpoint configuration
ENDPOINT_URL="https://mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de.us-central1-640132109143.prediction.vertexai.goog"
ENDPOINT_PROJECT="640132109143"
ENDPOINT_ID="mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de"

# Service name
SERVICE="medgemma-explica"

echo "=== MedGemma Explica - Deployment ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE}"
echo "Endpoint: ${ENDPOINT_ID} (project ${ENDPOINT_PROJECT})"
echo ""

# --- Deploy ---
echo "--- [1/2] Building & deploying ---"
gcloud run deploy "${SERVICE}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 4 \
  --set-env-vars "\
MEDGEMMA_PROJECT_ID=${PROJECT_ID},\
MEDGEMMA_LOCATION=${REGION},\
MEDGEMMA_GCS_BUCKET=${BUCKET_NAME},\
MEDGEMMA_MEDGEMMA_ENDPOINT_URL=${ENDPOINT_URL},\
MEDGEMMA_MEDGEMMA_ENDPOINT_PROJECT=${ENDPOINT_PROJECT},\
MEDGEMMA_MEDGEMMA_ENDPOINT_ID=${ENDPOINT_ID},\
MEDGEMMA_GEMINI_MODEL=gemini-3-flash-preview,\
MEDGEMMA_GEMINI_LOCATION=global,\
MEDGEMMA_DICOM_PROJECT=${PROJECT_ID},\
MEDGEMMA_DICOM_LOCATION=${REGION},\
MEDGEMMA_DICOM_DATASET=medgemma-dicom,\
MEDGEMMA_DICOM_STORE=ct-scans,\
MEDGEMMA_FRONTEND_URL=*"

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" --format="value(status.url)")

# --- Verify ---
echo ""
echo "--- [2/2] Verifying deployment ---"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/health" || true)
if [ "${HEALTH}" = "200" ]; then
  echo "Health check: OK"
else
  echo "Health check: ${HEALTH} (may need a moment to start)"
fi

echo ""
echo "=== Deployment complete ==="
echo ""
echo "App:      ${SERVICE_URL}"
echo "Health:   ${SERVICE_URL}/api/health"
echo "API Docs: ${SERVICE_URL}/docs"
