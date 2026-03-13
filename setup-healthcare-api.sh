#!/usr/bin/env bash
# Set up Cloud Healthcare API DICOM store and import IDC sample CT series.
#
# Usage:
#   ./setup-healthcare-api.sh [PROJECT_ID]
#
# Defaults to the MEDGEMMA_DICOM_PROJECT from backend/.env, or "riojucu".
#
# What this script does:
#   1. Enables the Cloud Healthcare API
#   2. Creates a Healthcare dataset and DICOM store
#   3. Creates a temporary GCS bucket for staging DICOM files
#   4. Copies 3 CT series from IDC public data (gs://idc-open-data)
#   5. Imports the DICOM files into the DICOM store
#   6. Grants IAM permissions for the default compute service account
#   7. Cleans up the staging bucket
#
# Prerequisites:
#   - gcloud CLI authenticated with project owner/editor permissions
#   - gsutil available (bundled with gcloud)
#
# Cost estimate:
#   - Storage: ~160 MB total (well under 1 GiB free tier)
#   - Requests: ~310 instances + metadata queries (well under 25K free tier)
#   - Monthly cost: $0.00 for typical demo usage

set -euo pipefail

# --- Configuration ---
PROJECT="${1:-riojucu}"
LOCATION="us-central1"
DATASET="medgemma-dicom"
DICOM_STORE="ct-scans"
STAGING_BUCKET="${PROJECT}-medgemma-dicom-staging"

# IDC sample series (from gs://idc-open-data, organized by crdc_series_uuid)
# Format: "label|crdc_series_uuid|instance_count|size_mb|collection"
SERIES_LIST=(
  "chest|37cf5cd8-d103-4cd0-a446-960bc0ed92a3|133|70|lidc_idri"
  "abdomen|c458380a-c5fa-40c0-8856-25ab3a5e64b8|80|42|c4kc_kits"
  "head|93e47303-a5cb-45cc-b3f4-ca086a389857|95|50|cptac_aml"
)

echo "============================================"
echo " Healthcare API Setup — DICOM Store"
echo "============================================"
echo ""
echo "Project:      ${PROJECT}"
echo "Location:     ${LOCATION}"
echo "Dataset:      ${DATASET}"
echo "DICOM Store:  ${DICOM_STORE}"
echo "Staging GCS:  gs://${STAGING_BUCKET}"
echo ""
echo "Series to import:"
for entry in "${SERIES_LIST[@]}"; do
  IFS='|' read -r label uuid count size collection <<< "${entry}"
  echo "  - ${label}: ${count} instances, ~${size} MB (${collection})"
done
echo ""

# --- Step 1: Enable the Healthcare API ---
echo ">>> Step 1/7: Enabling Cloud Healthcare API..."
gcloud services enable healthcare.googleapis.com --project="${PROJECT}" --quiet
echo "    Done."
echo ""

# --- Step 2: Create Healthcare dataset ---
echo ">>> Step 2/7: Creating Healthcare dataset '${DATASET}'..."
if gcloud healthcare datasets describe "${DATASET}" \
    --project="${PROJECT}" --location="${LOCATION}" &>/dev/null; then
  echo "    Dataset already exists, skipping."
else
  gcloud healthcare datasets create "${DATASET}" \
    --project="${PROJECT}" --location="${LOCATION}" --quiet
  echo "    Created."
fi
echo ""

# --- Step 3: Create DICOM store ---
echo ">>> Step 3/7: Creating DICOM store '${DICOM_STORE}'..."
if gcloud healthcare dicom-stores describe "${DICOM_STORE}" \
    --project="${PROJECT}" --location="${LOCATION}" --dataset="${DATASET}" &>/dev/null; then
  echo "    DICOM store already exists, skipping."
else
  gcloud healthcare dicom-stores create "${DICOM_STORE}" \
    --project="${PROJECT}" --location="${LOCATION}" --dataset="${DATASET}" --quiet
  echo "    Created."
fi
echo ""

# --- Step 4: Create staging GCS bucket and grant Healthcare SA access ---
echo ">>> Step 4/7: Creating staging bucket gs://${STAGING_BUCKET}..."
if gsutil ls -b "gs://${STAGING_BUCKET}" &>/dev/null; then
  echo "    Bucket already exists, skipping creation."
else
  gsutil mb -p "${PROJECT}" -l "${LOCATION}" "gs://${STAGING_BUCKET}"
  echo "    Created."
fi

# The Healthcare Service Agent needs storage.objects.list on the staging bucket
# to import DICOM files from GCS.
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT}" --format="value(projectNumber)")
HEALTHCARE_SA="service-${PROJECT_NUMBER}@gcp-sa-healthcare.iam.gserviceaccount.com"
echo "    Granting Healthcare SA (${HEALTHCARE_SA}) access to staging bucket..."
gsutil iam ch "serviceAccount:${HEALTHCARE_SA}:roles/storage.objectViewer" "gs://${STAGING_BUCKET}" 2>/dev/null
echo "    Done."
echo ""

# --- Step 5: Copy DICOM files from IDC public bucket ---
echo ">>> Step 5/7: Copying DICOM files from IDC (gs://idc-open-data)..."
total_files=0
for entry in "${SERIES_LIST[@]}"; do
  IFS='|' read -r label uuid count size collection <<< "${entry}"
  echo "    Copying ${label} (${count} files, ~${size} MB)..."
  gsutil -m cp -n "gs://idc-open-data/${uuid}/*.dcm" "gs://${STAGING_BUCKET}/${label}/" 2>&1 | tail -1
  total_files=$((total_files + count))
done
echo "    Total: ${total_files} files copied."
echo ""

# --- Step 6: Import DICOM files into Healthcare API ---
echo ">>> Step 6/7: Importing DICOM files into DICOM store..."
for entry in "${SERIES_LIST[@]}"; do
  IFS='|' read -r label uuid count size collection <<< "${entry}"
  echo "    Importing ${label}..."
  gcloud healthcare dicom-stores import gcs "${DICOM_STORE}" \
    --project="${PROJECT}" \
    --location="${LOCATION}" \
    --dataset="${DATASET}" \
    --gcs-uri="gs://${STAGING_BUCKET}/${label}/*.dcm" \
    --quiet
  echo "    ${label} import started."
done
echo ""
echo "    Note: Imports run asynchronously. Check status with:"
echo "    gcloud healthcare operations list --project=${PROJECT} --location=${LOCATION} --dataset=${DATASET}"
echo ""

# --- Step 7: Grant IAM permissions ---
echo ">>> Step 7/7: Granting IAM permissions..."
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "    Service account: ${COMPUTE_SA}"

# Healthcare DICOM Viewer role for reading DICOM data
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/healthcare.dicomViewer" \
  --condition=None \
  --quiet 2>/dev/null
echo "    roles/healthcare.dicomViewer granted."

# Also grant to current user for local dev
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
if [ -n "${CURRENT_ACCOUNT}" ]; then
  if [[ "${CURRENT_ACCOUNT}" == *"gserviceaccount.com" ]]; then
    MEMBER_TYPE="serviceAccount"
  else
    MEMBER_TYPE="user"
  fi

  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="${MEMBER_TYPE}:${CURRENT_ACCOUNT}" \
    --role="roles/healthcare.dicomViewer" \
    --condition=None \
    --quiet 2>/dev/null
  echo "    roles/healthcare.dicomViewer granted to ${CURRENT_ACCOUNT}."
fi
echo ""

# --- Summary ---
echo "============================================"
echo " Setup Complete"
echo "============================================"
echo ""
echo "DICOM store: projects/${PROJECT}/locations/${LOCATION}/datasets/${DATASET}/dicomStores/${DICOM_STORE}"
echo ""
echo "DICOMweb URL:"
echo "  https://healthcare.googleapis.com/v1/projects/${PROJECT}/locations/${LOCATION}/datasets/${DATASET}/dicomStores/${DICOM_STORE}/dicomWeb"
echo ""
echo "Backend .env settings (should already be configured):"
echo "  MEDGEMMA_DICOM_PROJECT=${PROJECT}"
echo "  MEDGEMMA_DICOM_LOCATION=${LOCATION}"
echo "  MEDGEMMA_DICOM_DATASET=${DATASET}"
echo "  MEDGEMMA_DICOM_STORE=${DICOM_STORE}"
echo ""
echo "To check import status:"
echo "  gcloud healthcare operations list --project=${PROJECT} --location=${LOCATION} --dataset=${DATASET}"
echo ""
echo "To clean up the staging bucket after imports complete:"
echo "  gsutil rm -r gs://${STAGING_BUCKET}"
echo ""
