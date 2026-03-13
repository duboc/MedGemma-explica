#!/usr/bin/env bash
# Grant IAM permissions for MedGemma Explica.
#
# Usage:
#   Same project:    ./setup-cross-project-access.sh <PROJECT_ID>
#   Cross-project:   ./setup-cross-project-access.sh <PROJECT_ID> <ENDPOINT_PROJECT_ID>
#
# When the MedGemma endpoint is in the SAME project, only one argument is
# needed. The script grants the Cloud Run service account access to
# Vertex AI, GCS, and Firestore within that project.
#
# When the endpoint is in a DIFFERENT project, pass both project IDs.
# The script additionally grants the Cloud Run SA access to call the
# endpoint in the remote project.
#
# You need IAM admin permissions on all referenced projects.

set -euo pipefail

THIS_PROJECT="${1:?Usage: ./setup-cross-project-access.sh <PROJECT_ID> [ENDPOINT_PROJECT_ID]}"
ENDPOINT_PROJECT="${2:-${THIS_PROJECT}}"

SAME_PROJECT=false
if [ "${THIS_PROJECT}" = "${ENDPOINT_PROJECT}" ]; then
  SAME_PROJECT=true
fi

echo "=== IAM Access Setup ==="
echo "Application project: ${THIS_PROJECT}"
if [ "${SAME_PROJECT}" = true ]; then
  echo "Endpoint project:    ${THIS_PROJECT} (same project)"
else
  echo "Endpoint project:    ${ENDPOINT_PROJECT} (cross-project)"
fi
echo ""

# Get project number for the Cloud Run service account
THIS_PROJECT_NUMBER=$(gcloud projects describe "${THIS_PROJECT}" --format="value(projectNumber)")
CLOUD_RUN_SA="${THIS_PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Cloud Run service account: ${CLOUD_RUN_SA}"

# --- Application project permissions ---
echo ""
echo "--- Granting permissions on application project (${THIS_PROJECT}) ---"

# Vertex AI User: for Gemini Flash calls
gcloud projects add-iam-policy-binding "${THIS_PROJECT}" \
  --member="serviceAccount:${CLOUD_RUN_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet
echo "  roles/aiplatform.user (Vertex AI / Gemini Flash)"

# GCS: for image storage
gcloud projects add-iam-policy-binding "${THIS_PROJECT}" \
  --member="serviceAccount:${CLOUD_RUN_SA}" \
  --role="roles/storage.objectAdmin" \
  --condition=None \
  --quiet
echo "  roles/storage.objectAdmin (Cloud Storage)"

# Firestore: for analysis persistence
gcloud projects add-iam-policy-binding "${THIS_PROJECT}" \
  --member="serviceAccount:${CLOUD_RUN_SA}" \
  --role="roles/datastore.user" \
  --condition=None \
  --quiet
echo "  roles/datastore.user (Firestore)"

# --- Cross-project endpoint permissions (only if different project) ---
if [ "${SAME_PROJECT}" = false ]; then
  echo ""
  echo "--- Granting permissions on endpoint project (${ENDPOINT_PROJECT}) ---"

  gcloud projects add-iam-policy-binding "${ENDPOINT_PROJECT}" \
    --member="serviceAccount:${CLOUD_RUN_SA}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet
  echo "  roles/aiplatform.user (MedGemma endpoint access)"
fi

# --- Local development access ---
echo ""
echo "--- Granting local development access ---"

CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
if [ -n "${CURRENT_ACCOUNT}" ]; then
  echo "Current gcloud account: ${CURRENT_ACCOUNT}"

  if [[ "${CURRENT_ACCOUNT}" == *"gserviceaccount.com" ]]; then
    MEMBER_TYPE="serviceAccount"
  else
    MEMBER_TYPE="user"
  fi

  # Grant on the endpoint project (same or different)
  gcloud projects add-iam-policy-binding "${ENDPOINT_PROJECT}" \
    --member="${MEMBER_TYPE}:${CURRENT_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet
  echo "  roles/aiplatform.user on ${ENDPOINT_PROJECT}"

  # If cross-project, also grant on the app project for Gemini
  if [ "${SAME_PROJECT}" = false ]; then
    gcloud projects add-iam-policy-binding "${THIS_PROJECT}" \
      --member="${MEMBER_TYPE}:${CURRENT_ACCOUNT}" \
      --role="roles/aiplatform.user" \
      --condition=None \
      --quiet
    echo "  roles/aiplatform.user on ${THIS_PROJECT}"
  fi
else
  echo "  WARNING: Could not determine current gcloud account."
  echo "  Manually grant roles/aiplatform.user on the endpoint project."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Permissions granted on ${THIS_PROJECT}:"
echo "  ${CLOUD_RUN_SA} -> aiplatform.user, storage.objectAdmin, datastore.user"
if [ "${SAME_PROJECT}" = false ]; then
  echo ""
  echo "Permissions granted on ${ENDPOINT_PROJECT}:"
  echo "  ${CLOUD_RUN_SA} -> aiplatform.user"
fi
echo ""
echo "Next: ./deploy.sh"
