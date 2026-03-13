# MedGemma Explica

An educational chest X-ray anatomy localization tool powered by Google's **MedGemma 1.5** and **Gemini Flash** on Vertex AI. Upload or select an X-ray image, identify anatomical structures with bounding boxes, and explore educational deep dives, findings reports, and interactive Q&A.

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
              +-----+-----+
              |           |
         Cloud Storage  Firestore
         (images)       (analyses)
```

**Two-model pipeline:**

1. **MedGemma 1.5** (medical vision model) -- analyzes the X-ray image, generates bounding boxes, and produces raw medical text
2. **Gemini Flash** (general model) -- structures the raw text into JSON schemas for rich UI rendering, powers Q&A chat, and generates educational explanations

## Features

- **Structure Localization** -- identify anatomical structures with bounding boxes drawn on the X-ray
- **Findings Tab** -- per-structure observations with normal/abnormal/borderline status badges
- **Full Report** -- comprehensive findings report with ABCDE systematic reading, pathology scenarios, and clinical pearls
- **Deep Dive** -- educational breakdown at four levels (pre-med through attending)
- **Q&A Chat** -- multi-turn conversation about the X-ray with AI-generated suggested questions
- **Mock Mode** -- full UI testing without any GCP credentials

## MedGemma Endpoint & IAM

The backend calls two Vertex AI models: **MedGemma 1.5** (for image analysis) and **Gemini Flash** (for text structuring and chat). Both use Application Default Credentials (ADC).

The MedGemma endpoint can live in the **same project** as the application or in a **different project**. The setup script handles both cases.

### Same project

Everything runs in one GCP project. The Cloud Run service account needs Vertex AI, GCS, and Firestore access within that project.

```
Your Project
+-------------------------------------------+
|  Cloud Run (backend)                      |
|    SA: <num>-compute@developer.gsa.com    |
|      needs: aiplatform.user               |
|             storage.objectAdmin           |
|             datastore.user                |
|                                           |
|  Vertex AI Endpoint (MedGemma 1.5)        |
|  Vertex AI API (Gemini Flash)             |
|  Cloud Storage (images)                   |
|  Firestore (analyses)                     |
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
+-----------------------------------+      +-----------------------------------+
```

### Configuration

All settings use environment variables with the `MEDGEMMA_` prefix:

| Variable | Description | Example |
|----------|-------------|---------|
| `MEDGEMMA_PROJECT_ID` | Application GCP project ID | `my-project` |
| `MEDGEMMA_LOCATION` | Cloud Run & Vertex AI region | `us-central1` |
| `MEDGEMMA_GCS_BUCKET` | GCS bucket for images | `my-project-medgemma-explica` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_URL` | Full endpoint URL | `https://mg-endpoint-....prediction.vertexai.goog` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_PROJECT` | Project **number** hosting the endpoint | `640132109143` |
| `MEDGEMMA_MEDGEMMA_ENDPOINT_ID` | Endpoint ID | `mg-endpoint-b2729fdc-...` |
| `MEDGEMMA_GEMINI_MODEL` | Gemini model for structuring/chat | `gemini-3-flash-preview` |
| `MEDGEMMA_GEMINI_LOCATION` | Gemini API location | `global` |
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

### 1. Setup infrastructure

```bash
./setup-infra.sh <PROJECT_ID> [REGION]
```

Enables required APIs (Vertex AI, Cloud Run, Cloud Build, Firestore, Storage, Artifact Registry), creates a GCS bucket, Firestore database, and Artifact Registry repo.

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
│   ├── main.py                 # FastAPI app & endpoints
│   ├── config.py               # Pydantic settings (env vars)
│   ├── vertex_ai.py            # MedGemma prediction & chat
│   ├── gemini_flash.py         # Gemini Flash API wrapper
│   ├── deep_dive.py            # Educational deep dive pipeline
│   ├── findings_report.py      # Structured findings report pipeline
│   ├── firestore_db.py         # Firestore operations
│   ├── storage.py              # GCS operations
│   ├── image_processing.py     # Image preprocessing
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main application
│   │   ├── components/         # React components
│   │   ├── hooks/useApi.ts     # API client
│   │   ├── types/index.ts      # TypeScript interfaces
│   │   └── utils/markdown.ts   # Markdown rendering
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf              # Production nginx config
│   └── Dockerfile
├── sample-xrays/               # Pre-loaded sample images
├── docs/                       # Design documents
├── deploy.sh                   # Cloud Run deployment
├── setup-infra.sh              # GCP infrastructure setup
├── setup-cross-project-access.sh  # IAM setup (same or cross-project)
└── run-local.sh                # Local development launcher
```

## API Endpoints

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

Full API docs available at `/docs` when the backend is running.

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite
- **Backend:** FastAPI, Python 3.12
- **AI Models:** MedGemma 1.5 (Vertex AI), Gemini Flash (Vertex AI)
- **Storage:** Google Cloud Storage, Firestore
- **Deployment:** Cloud Run (deploy from source)

## License

MIT
