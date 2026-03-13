# CT Scan Analysis - Architecture & Design Decisions

## Overview

The CT scan demo analyzes computed tomography series using MedGemma 1.5 on Vertex AI.
CT data is sourced from Imaging Data Commons (IDC) public archive, stored in a
Google Cloud Healthcare API DICOM store, and rendered as PNG frames for analysis.

## Architecture

```
CT_SAMPLES (pre-configured IDC series)
        |
        v
  Healthcare API DICOM Store
  (riojucu / medgemma-dicom / ct-scans)
        |
        | 1. Fetch instance metadata (DICOMweb)
        | 2. Sample N slices evenly
        | 3. Download rendered PNGs (/rendered endpoint)
        v
  Backend (ct_dicom.py)
        |
        | base64-encoded PNG frames as image_url parts
        v
  MedGemma 1.5 Endpoint (Vertex AI)
        |
        | Text analysis (no bounding boxes)
        v
  Frontend (CTApp.tsx)
```

## Key Design Decision: Rendered PNGs vs image_dicom

### The Official Notebook Approach

Google's official MedGemma CT notebook uses `image_dicom` message type:

```json
{
  "type": "image_dicom",
  "image_dicom": {
    "dicom_source": ["https://healthcare.googleapis.com/.../instances/1.2.3.4"],
    "access_credential": "BEARER_TOKEN"
  }
}
```

In this approach:
- The **model itself** fetches DICOM data from the DICOMweb store
- The model controls windowing/leveling for optimal viewing
- Up to **85 slices** are sent per analysis
- Requires MedGemma 1.5 endpoint deployed with **image limit >= 85**
- Uses Google's public DICOM store: `projects/hai-cd3-foundations/locations/us-central1/datasets/public/dicomStores/test-images`

### Our Approach: Rendered PNG Frames

We use the DICOMweb **rendered endpoint** to download pre-rendered PNG frames,
then send them as standard `image_url` base64 parts:

```json
{
  "type": "image_url",
  "image_url": {"url": "data:image/png;base64,..."}
}
```

**Why this approach:**

1. **Endpoint compatibility**: Our MedGemma endpoint returned
   `{'error': {'code': 400, 'message': 'Unknown part type: image_dicom None'}}`
   when sent `image_dicom` messages. The endpoint was not deployed with
   MedGemma 1.5's CT-specific configuration (85 image limit).

2. **Simpler deployment**: The `image_url` approach works with any MedGemma
   endpoint that accepts images, without requiring specific deployment settings.

3. **Same API pattern as X-ray**: Both X-ray and CT use `image_url` base64,
   keeping the `_call_medgemma()` function universal.

**Trade-offs:**

| Aspect | image_dicom (notebook) | Rendered PNG (ours) |
|--------|----------------------|---------------------|
| Slices sent | 85 | 12 (configurable via MAX_SLICES_FOR_ANALYSIS) |
| Image quality | Raw DICOM (model controls W/L) | Pre-rendered PNG (server default W/L) |
| Payload size | URLs only (~10 KB) | ~1.9 MB base64 (12 x ~160 KB) |
| Endpoint requirement | MedGemma 1.5, 85 image limit | Any MedGemma with image support |
| Auth model | Bearer token passed to model | Bearer token used server-side |
| DICOM store access | Model needs network access | Backend needs network access |

### Upgrading to image_dicom

To switch to the notebook's approach in the future:

1. **Re-deploy MedGemma endpoint** from Model Garden with:
   - MedGemma 1.5 model variant
   - Image limit set to **85** (under Deployment Settings > Serving spec)
   - Dedicated endpoint type

2. **Update `ct_dicom.py`**:
   - Replace `fetch_rendered_slices()` with URL-based approach
   - Build `image_dicom` message parts with DICOMweb instance URLs
   - Pass `access_credential` (bearer token) in the message

3. **Update `vertex_ai.py`**:
   - May need to switch from `:predict` to `raw_predict` with
     `use_dedicated_endpoint=True` (as the notebook does)

4. **Optionally use Google's public store** at `hai-cd3-foundations` instead of
   (or alongside) the `riojucu` store.

## Data Pipeline

### DICOM Store Setup

The `setup-healthcare-api.sh` script automates provisioning:

1. Enables Cloud Healthcare API
2. Creates Healthcare dataset (`medgemma-dicom`) and DICOM store (`ct-scans`)
3. Creates a staging GCS bucket
4. Copies DICOM files from IDC public data (`gs://idc-open-data/`)
5. Imports files into the DICOM store
6. Grants IAM permissions
7. Cleans up staging bucket

### Sample Series

| ID | Collection | Body Part | Slices | Source |
|----|-----------|-----------|--------|--------|
| chest_ct | LIDC-IDRI | Thorax | 133 | Lung CT screening |
| abdomen_ct | C4KC-KiTS | Abdomen | 80 | Renal CT with contrast |
| head_ct | CPTAC-AML | Head | 95 | Head CT without contrast |

Series UIDs were verified using the `idc-index` Python package against the
IDC DuckDB index, and cross-referenced with `gs://idc-open-data/`.

### Rendered Frame Retrieval

```
GET /studies/{study}/series/{series}/instances/{sop}/rendered
Accept: image/png
Authorization: Bearer {token}
```

- Returns a 512x512 PNG (~120 KB per slice)
- Uses the Healthcare API's default window/level settings
- 12 slices are sampled evenly across the volume using `_sample_indices()`
- Downloads run in parallel (6 workers) for ~2-3 second total fetch time

## Cost

Healthcare API costs for this demo are negligible:
- **Storage**: ~160 MB total (well under 1 GiB free tier)
- **Requests**: ~310 instances + metadata queries (well under 25K/month free tier)
- **Rendered frames**: 12 per analysis (part of the request quota)
- **Monthly cost**: $0.00 for typical demo usage

## Frontend

The CT app (`/ct`) is simpler than the X-ray app:
- No file upload (pre-configured samples only)
- No bounding boxes (text analysis only)
- No structure selector (free-text query instead)
- Reuses Header, Disclaimer, HistoryPanel components
- Has its own ExplainPanel and ChatPanel (CT-specific, use Gemini Flash)
