#!/usr/bin/env bash
# Deploy MedGemma Explica to Cloud Run (from source)
#
# Usage: ./deploy.sh [REGION]
#
# Deploys both the backend (FastAPI) and frontend (React/nginx) as
# separate Cloud Run services. The frontend gets the backend URL
# baked in at build time via VITE_API_URL.
#
# Prerequisites:
#   1. ./setup-infra.sh <PROJECT_ID>
#   2. If the MedGemma endpoint is in a DIFFERENT project:
#      ./setup-cross-project-access.sh <PROJECT_ID> <ENDPOINT_PROJECT_ID>
#   3. A deployed MedGemma endpoint (note the URL, project number, and ID)

set -euo pipefail

# --- Configuration ---
PROJECT_ID="canelaverde"
REGION="${1:-us-central1}"
BUCKET_NAME="${PROJECT_ID}-medgemma-explica"

# MedGemma endpoint configuration
# If the endpoint is in the SAME project, ENDPOINT_PROJECT should be the
# project number of PROJECT_ID. Find it with:
#   gcloud projects describe <PROJECT_ID> --format="value(projectNumber)"
ENDPOINT_URL="https://mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de.us-central1-640132109143.prediction.vertexai.goog"
ENDPOINT_PROJECT="640132109143"
ENDPOINT_ID="mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de"

# Service names
BACKEND_SERVICE="medgemma-explica-api"
FRONTEND_SERVICE="medgemma-explica-ui"

echo "=== MedGemma Explica - Deployment ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Endpoint: ${ENDPOINT_ID} (project ${ENDPOINT_PROJECT})"
echo ""

# --- Deploy backend ---
echo "--- [1/4] Deploying backend ---"
gcloud run deploy "${BACKEND_SERVICE}" \
  --source backend/ \
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
MEDGEMMA_FRONTEND_URL=*"

# Get backend URL
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" --format="value(status.url)")
echo "Backend deployed at: ${BACKEND_URL}"

# --- Deploy frontend ---
echo ""
echo "--- [2/4] Deploying frontend ---"

# Write a temporary .env.production for the Vite build
echo "VITE_API_URL=${BACKEND_URL}" > frontend/.env.production

gcloud run deploy "${FRONTEND_SERVICE}" \
  --source frontend/ \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2

# Clean up temp env file
rm -f frontend/.env.production

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" --format="value(status.url)")

# --- Update CORS ---
echo ""
echo "--- [3/4] Updating backend CORS ---"
gcloud run services update "${BACKEND_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --update-env-vars "MEDGEMMA_FRONTEND_URL=${FRONTEND_URL}"

# --- Verify ---
echo ""
echo "--- [4/4] Verifying deployment ---"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/health" || true)
if [ "${HEALTH}" = "200" ]; then
  echo "Backend health check: OK"
else
  echo "Backend health check: ${HEALTH} (may need a moment to start)"
fi

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Frontend: ${FRONTEND_URL}"
echo "Backend:  ${BACKEND_URL}"
echo "Health:   ${BACKEND_URL}/api/health"
echo "API Docs: ${BACKEND_URL}/docs"
