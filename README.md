# MedGemma Explica

An educational medical imaging analysis tool powered by Google's **MedGemma 1.5** and **Gemini Flash** on Vertex AI. Supports both **Chest X-ray** analysis with anatomical localization and **CT scan** analysis with structured radiology reports.

## Architecture

```
Frontend (React + Vite)           Backend (FastAPI)
       |                                |
       | REST API                       |--- Gemini Flash (Vertex AI)
       +------>  Cloud Run  <-----------+       structuring & Q&A
                    |                   |
                    |                   |--- MedGemma 1.5 (Vertex AI)
                    |                        image analysis & localization
                    |
              +-----+-----+-----+
              |           |     |
         Cloud Storage  Firestore  Healthcare API
         (X-ray images) (analyses) (DICOM CT scans)
```

**Two-model pipeline:**

1. **MedGemma 1.5** (medical vision model) -- analyzes images (X-ray or CT slices), generates bounding boxes (X-ray), and produces raw medical text
2. **Gemini Flash** (general model) -- structures the raw text into JSON schemas for rich UI rendering, powers Q&A chat, and generates educational explanations

**Landing page** lets users choose between the X-ray and CT scan demos.

## Features

### X-ray Demo
- **Structure Localization** -- identify anatomical structures with bounding boxes drawn on the X-ray
- **Findings Tab** -- per-structure observations with normal/abnormal/borderline status badges
- **Full Report** -- comprehensive findings report with ABCDE systematic reading, pathology scenarios, and clinical pearls
- **Deep Dive** -- educational breakdown at four levels (pre-med through attending)
- **Q&A Chat** -- multi-turn conversation about the X-ray with AI-generated suggested questions

### CT Scan Demo
- **Series Picker** -- select from pre-loaded CT cases (chest, abdomen, head)
- **Slice Viewer** -- interactive CT slice navigation with scroll, drag, keyboard, and slider controls
- **Structured Report (Laudo)** -- MedGemma analyzes rendered PNG slices, then Gemini Flash structures the output into a rich report with:
  - Technique details (exam type, plane, thickness, contrast)
  - Findings by region with status badges and expandable sub-items
  - Diagnostic impressions with severity indicators (critical/important/minor/normal)
  - Differential diagnoses
  - Recommendations with urgency badges
- **Deep Dive** -- CT-specific educational explanations
- **Q&A Chat** -- ask follow-up questions about the CT analysis

### Shared
- **Mock Mode** -- full UI testing without any GCP credentials
- **History Panel** -- browse and recall previous analyses
- **Portuguese (PT-BR)** -- all content in Brazilian Portuguese

## MedGemma Endpoint & IAM

The backend calls two Vertex AI models: **MedGemma 1.5** (for image analysis) and **Gemini Flash** (for text structuring and chat). Both use Application Default Credentials (ADC).

The MedGemma endpoint can live in the **same project** as the application or in a **different project**. The setup script handles both cases.

### Same project

```
Your Project
+-------------------------------------------+
|  Cloud Run (backend)                      |
|    SA: <num>-compute@developer.gsa.com    |
|      needs: aiplatform.user               |
|             storage.objectAdmin           |
|             datastore.user                |
|             healthcare.dicomViewer (CT)    |
|                                           |
|  Vertex AI Endpoint (MedGemma 1.5)        |
|  Vertex AI API (Gemini Flash)             |
|  Cloud Storage (X-ray images)             |
|  Firestore (analyses)                     |
|  Healthcare API (DICOM CT scans)          |
+-------------------------------------------+
```

### Cross-project

The MedGemma endpoint is hosted in a separate project (e.g., a shared ML platform). The Cloud Run SA needs additional `aiplatform.user` on that remote project.

```
Application Project                        Endpoint Project
+-----------------------------------+      +-----------------------------------+
|  Cloud Run (backend)              |      |  Vertex AI Endpoint               |
|    SA: <num>-compute@...          | ---> |    MedGemma 1.5                   |
|                                   |      |                                   |
|  Gemini Flash (Vertex AI)         |      |  IAM:                             |
|  Cloud Storage                    |      |    roles/aiplatform.user granted  |
|  Firestore                        |      |    to the Cloud Run SA            |
|  Healthcare API (DICOM)           |      |                                   |
+-----------------------------------+      +-----------------------------------+
```

### Configuration

All settings use environment variables with the `MEDGEMMA_` prefix:

| Variable | Description | Example |
|----------|-------------|---------|
| `MEDGEMMA_PROJECT_ID` | Application GCP project ID | `my-project` |
| `MEDGEMMA_LOCATION` | Cloud Run & Vertex AI region | `us-central1` |
| `MEDGEMMA_GCS_BUCKET` | GCS bucket for X-ray images | `my-project-medgemma-explica` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_URL` | Full endpoint URL | `https://mg-endpoint-....prediction.vertexai.goog` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_PROJECT` | Project **number** hosting the endpoint | `640132109143` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_ID` | Endpoint ID | `mg-endpoint-b2729fdc-...` |
| `MEDGEMMA_GEMINI_MODEL` | Gemini model for structuring/chat | `gemini-3-flash-preview` |
| `MEDGEMMA_GEMINI_LOCATION` | Gemini API location | `global` |
| `MEDGEMMA_DICOM_PROJECT` | GCP project for Healthcare API | `my-project` |
| `MEDGEMMA_DICOM_LOCATION` | Healthcare API region | `us-central1` |
| `MEDGEMMA_DICOM_DATASET` | Healthcare API dataset name | `medgemma-dicom` |
| `MEDGEMMA_DICOM_STORE` | DICOM store name | `ct-scans` |
| `MEDGEMMA_FRONTEND_URL` | Frontend URL for CORS | `https://medgemma-explica-ui-....run.app` |

> **Note:** `MEDGEMMA_MEDGEMMA_ENDPOINT_PROJECT` requires the project **number**, not the project ID. Find it with:
> ```bash
> gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"
> ```

## Setup & Deployment

### Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- A GCP project with billing enabled
- A deployed MedGemma 1.5 endpoint (via [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden))
- (For CT) A Healthcare API DICOM store with imported CT studies (see `scripts/setup_healthcare_api.sh`)

### 1. Setup infrastructure

```bash
./setup-infra.sh <PROJECT_ID> [REGION]
```

Enables required APIs (Vertex AI, Cloud Run, Cloud Build, Firestore, Storage, Artifact Registry, Healthcare API), creates a GCS bucket, Firestore database, and Artifact Registry repo.

### 2. Grant IAM permissions

**Same project** (endpoint in the same project as the app):

```bash
./setup-cross-project-access.sh <PROJECT_ID>
```

**Cross-project** (endpoint in a different project):

```bash
./setup-cross-project-access.sh <PROJECT_ID> <ENDPOINT_PROJECT_ID>
```

The script grants:
- `roles/aiplatform.user` -- Vertex AI access (MedGemma + Gemini Flash)
- `roles/storage.objectAdmin` -- GCS image storage
- `roles/datastore.user` -- Firestore persistence
- `roles/healthcare.dicomViewer` -- Healthcare API DICOM access (CT)
- Local dev access for your current gcloud account
- (Cross-project only) `roles/aiplatform.user` on the endpoint project

### 3. Update deploy.sh configuration

Edit `deploy.sh` and set your endpoint details:

```bash
PROJECT_ID="your-project-id"
ENDPOINT_URL="https://your-endpoint-url.prediction.vertexai.goog"
ENDPOINT_PROJECT="your-endpoint-project-number"   # same or different project number
ENDPOINT_ID="your-endpoint-id"
```

### 4. Deploy to Cloud Run

```bash
./deploy.sh [REGION]
```

This deploys both services from source using `gcloud run deploy --source`:
- **Backend** (`medgemma-explica-api`) -- FastAPI, 1Gi memory, 2 CPUs
- **Frontend** (`medgemma-explica-ui`) -- React/nginx, 256Mi memory

The script automatically:
1. Deploys the backend and retrieves its URL
2. Builds the frontend with `VITE_API_URL` pointing to the backend
3. Deploys the frontend
4. Updates the backend CORS with the frontend URL
5. Runs a health check

## Local Development

### Quick start (mock mode)

Mock mode runs the full UI with fake data -- no GCP credentials needed:

```bash
./run-local.sh
```

Open http://localhost:3000 and toggle "Mock Mode" in the header.

### With live GCP

1. Authenticate:
   ```bash
   gcloud auth application-default login
   ```

2. Grant your account access:
   ```bash
   # Same project
   ./setup-cross-project-access.sh <PROJECT_ID>

   # Cross-project
   ./setup-cross-project-access.sh <PROJECT_ID> <ENDPOINT_PROJECT_ID>
   ```

3. Start:
   ```bash
   ./run-local.sh
   ```

4. Open http://localhost:3000

### Manual setup

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
MedGemma-explica/
├── backend/
│   ├── main.py                 # FastAPI app & all endpoints (X-ray + CT)
│   ├── config.py               # Pydantic settings (env vars)
│   ├── vertex_ai.py            # MedGemma prediction & chat
│   ├── gemini_flash.py         # Gemini Flash API wrapper
│   ├── deep_dive.py            # Educational deep dive pipeline
│   ├── findings_report.py      # X-ray structured findings report
│   ├── ct_dicom.py             # CT DICOM operations (Healthcare API)
│   ├── ct_findings_report.py   # CT structured report (Gemini Flash)
│   ├── firestore_db.py         # Firestore operations
│   ├── storage.py              # GCS operations
│   ├── image_processing.py     # Image preprocessing
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # X-ray main application
│   │   ├── CTApp.tsx           # CT scan main application
│   │   ├── LandingPage.tsx     # Landing page (X-ray / CT chooser)
│   │   ├── components/
│   │   │   ├── ResultViewer.tsx      # X-ray result tabs
│   │   │   ├── FindingsReport.tsx    # X-ray structured report UI
│   │   │   ├── CTResultViewer.tsx    # CT result tabs
│   │   │   ├── CTFindingsReport.tsx  # CT structured report UI
│   │   │   ├── CTSeriesPicker.tsx    # CT series selection
│   │   │   ├── CTSliceViewer.tsx     # CT slice navigation
│   │   │   ├── HistoryPanel.tsx      # Analysis history
│   │   │   ├── Header.tsx           # Shared header
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   ├── useApi.ts       # X-ray API client
│   │   │   └── useCtApi.ts     # CT API client
│   │   ├── types/index.ts      # TypeScript interfaces
│   │   └── utils/markdown.ts   # Markdown rendering
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf              # Production nginx config
│   └── Dockerfile
├── docs/
│   ├── ct-architecture.md      # CT rendered PNG vs image_dicom decision
│   ├── ct-viewer-options.md    # DICOM viewer comparison
│   └── ...
├── examples/                   # Sample analyses
├── sample-xrays/               # Pre-loaded X-ray sample images
├── scripts/                    # Setup scripts
├── deploy.sh                   # Cloud Run deployment
├── setup-infra.sh              # GCP infrastructure setup
├── setup-cross-project-access.sh  # IAM setup (same or cross-project)
└── run-local.sh                # Local development launcher
```

## API Endpoints

### X-ray

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/samples` | List sample X-ray images |
| `GET` | `/api/structures` | List anatomical structures |
| `POST` | `/api/analyze` | Analyze an X-ray image |
| `POST` | `/api/findings-report` | Generate comprehensive findings report |
| `POST` | `/api/explain` | Generate educational deep dive |
| `POST` | `/api/chat` | Multi-turn Q&A about the X-ray |
| `POST` | `/api/suggest-questions` | Generate suggested questions |
| `POST` | `/api/structure-findings` | Extract per-structure observations |
| `GET` | `/api/analyses` | List recent analyses |
| `GET` | `/api/analyses/{id}` | Get specific analysis |
| `PATCH` | `/api/analyses/{id}` | Update analysis fields |
| `DELETE` | `/api/analyses/{id}` | Delete analysis |

### CT Scan

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/ct/samples` | List available CT series |
| `GET` | `/api/ct/frames/{series_id}` | Get rendered PNG frames for a series |
| `POST` | `/api/ct/analyze` | Analyze CT series with MedGemma |
| `POST` | `/api/ct/parse-report` | Structure CT analysis into JSON via Gemini Flash |
| `POST` | `/api/ct/explain` | CT-specific educational deep dive |
| `POST` | `/api/ct/chat` | Multi-turn Q&A about CT analysis |
| `POST` | `/api/ct/suggest-questions` | Generate CT-specific suggested questions |
| `GET` | `/api/ct/analyses` | List recent CT analyses |
| `GET` | `/api/ct/analyses/{id}` | Get specific CT analysis |
| `PATCH` | `/api/ct/analyses/{id}` | Update CT analysis fields |
| `DELETE` | `/api/ct/analyses/{id}` | Delete CT analysis |

Full API docs available at `/docs` when the backend is running.

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite
- **Backend:** FastAPI, Python 3.12
- **AI Models:** MedGemma 1.5 (Vertex AI), Gemini Flash (Vertex AI)
- **Storage:** Google Cloud Storage, Firestore, Cloud Healthcare API (DICOM)
- **Deployment:** Cloud Run (deploy from source)

## License

MIT
