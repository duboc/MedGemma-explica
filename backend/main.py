import io
import logging
import os
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from config import settings
from ct_dicom import CT_SAMPLES, fetch_rendered_slices, mock_ct_analyze
from image_processing import pad_image_to_square
from vertex_ai import ANATOMY_INFO, get_educational_info, mock_predict

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MedGemma Explica API",
    description="Educational chest X-ray anatomy localization with MedGemma 1.5",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/dicom", "image/webp"}

SAMPLE_IMAGES = [
    {
        "id": "normal_pa",
        "name": "Normal PA Chest X-ray",
        "filename": "normal_pa_chest_xray.jpg",
        "source": "Wikimedia Commons (CC0)",
        "description": "PA chest X-ray of a healthy individual showing normal anatomy.",
    },
    {
        "id": "pa_wikimedia",
        "name": "PA Chest X-ray (Wikimedia)",
        "filename": "chest_xray_pa_wikimedia.png",
        "source": "Wikimedia Commons (CC0, Stillwaterising)",
        "description": "Standard posteroanterior chest radiograph.",
    },
    {
        "id": "openi_normal",
        "name": "Normal Chest X-ray (OpenI)",
        "filename": "openi_normal_cxr_1.png",
        "source": "NLM OpenI / PMC4663864 (Open Access)",
        "description": "Normal chest X-ray from NIH Open-i collection.",
    },
]

# In-memory store for mock analyses
_mock_analyses: list[dict] = []
_LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
_SAMPLE_XRAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "sample-xrays")


def _ensure_uploads_dir():
    os.makedirs(_LOCAL_UPLOAD_DIR, exist_ok=True)


def _save_local_image(file_bytes: bytes, filename: str) -> str:
    _ensure_uploads_dir()
    unique = uuid.uuid4().hex[:8]
    safe_name = f"{unique}_{filename}"
    path = os.path.join(_LOCAL_UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return safe_name


_ensure_uploads_dir()
app.mount("/uploads", StaticFiles(directory=_LOCAL_UPLOAD_DIR), name="uploads")

if os.path.isdir(_SAMPLE_XRAYS_DIR):
    app.mount("/sample-xrays", StaticFiles(directory=_SAMPLE_XRAYS_DIR), name="sample-xrays")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/samples")
def list_samples():
    """List pre-loaded sample chest X-ray images."""
    return [{**s, "url": f"/sample-xrays/{s['filename']}"} for s in SAMPLE_IMAGES]


@app.get("/api/structures")
def list_structures():
    """List available anatomical structures with educational info."""
    return [{"name": name, **info} for name, info in ANATOMY_INFO.items()]


@app.post("/api/analyze")
async def analyze(
    object_name: str = Form(...),
    mock: bool = Form(False),
    file: UploadFile | None = File(None),
    sample_id: str | None = Form(None),
):
    """Upload an X-ray image (or pick a sample) and localize anatomical structures.

    object_name can be a single structure or comma-separated list for multi-structure analysis.
    """
    if not file and not sample_id:
        raise HTTPException(400, "Provide either an image file or a sample_id")

    # Parse multi-structure input
    structure_names = [s.strip() for s in object_name.split(",") if s.strip()]
    if not structure_names:
        raise HTTPException(400, "At least one anatomical structure is required")
    if len(structure_names) > 8:
        raise HTTPException(400, "Maximum 8 structures per analysis")

    if file:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(400, f"Unsupported file type: {file.content_type}")
        file_bytes = await file.read()
        if len(file_bytes) > 20 * 1024 * 1024:
            raise HTTPException(400, "File size exceeds 20MB limit")
        source_filename = file.filename or "upload.png"
    else:
        sample = next((s for s in SAMPLE_IMAGES if s["id"] == sample_id), None)
        if not sample:
            raise HTTPException(400, f"Unknown sample_id: {sample_id}")
        sample_path = os.path.join(_SAMPLE_XRAYS_DIR, sample["filename"])
        if not os.path.isfile(sample_path):
            raise HTTPException(500, "Sample image file not found on server")
        with open(sample_path, "rb") as f:
            file_bytes = f.read()
        source_filename = sample["filename"]

    # Preprocess: pad to square
    image = Image.open(io.BytesIO(file_bytes))
    padded_image = pad_image_to_square(image)

    buf = io.BytesIO()
    padded_image.save(buf, format="PNG")
    padded_bytes = buf.getvalue()

    display_name = ", ".join(structure_names)

    if mock:
        # Mock mode: local storage + fake bounding boxes
        saved_name = _save_local_image(padded_bytes, source_filename)
        image_url = f"/uploads/{saved_name}"
        all_boxes = []
        all_responses = []
        edu_infos = []
        for name in structure_names:
            response_text, bounding_boxes = mock_predict(name)
            all_boxes.extend(bounding_boxes)
            all_responses.append(f"[{name}] {response_text}")
            edu_infos.append(get_educational_info(name))
        doc_id = uuid.uuid4().hex
        analysis = {
            "id": doc_id,
            "object_name": display_name,
            "structure_names": structure_names,
            "response_text": "\n\n".join(all_responses),
            "bounding_boxes": all_boxes,
            "image_url": image_url,
            "image_blob_path": saved_name,
            "image_width": padded_image.width,
            "image_height": padded_image.height,
            "educational_info": edu_infos[0] if edu_infos else {},
            "educational_infos": edu_infos,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mock": True,
        }
        _mock_analyses.insert(0, analysis)
        if len(_mock_analyses) > 100:
            _mock_analyses[:] = _mock_analyses[:100]
        return analysis
    else:
        # Real mode: GCS + Vertex AI + Firestore
        try:
            from storage import upload_image
            from firestore_db import save_analysis
            from vertex_ai import predict_with_medgemma
        except ImportError:
            raise HTTPException(
                503,
                "Live mode unavailable: Google Cloud dependencies not installed. Use Mock Mode instead.",
            )

        content_type = file.content_type if file else "image/png"
        blob_path = upload_image(file_bytes, source_filename, content_type)
        _save_local_image(padded_bytes, blob_path.replace("/", "_"))

        # Parallelize MedGemma calls across structures
        def _predict(name: str):
            resp, boxes = predict_with_medgemma(padded_bytes, name)
            return name, resp, boxes

        all_boxes = []
        all_responses = []
        edu_infos = []

        if len(structure_names) == 1:
            name = structure_names[0]
            resp, boxes = predict_with_medgemma(padded_bytes, name)
            all_boxes.extend(boxes)
            all_responses.append(f"[{name}] {resp}")
            edu_infos.append(get_educational_info(name))
        else:
            results_map: dict[str, tuple[str, list]] = {}
            with ThreadPoolExecutor(max_workers=min(len(structure_names), 4)) as pool:
                futures = {pool.submit(_predict, n): n for n in structure_names}
                for fut in as_completed(futures):
                    name, resp, boxes = fut.result()
                    results_map[name] = (resp, boxes)
            # Preserve original order
            for name in structure_names:
                resp, boxes = results_map[name]
                all_boxes.extend(boxes)
                all_responses.append(f"[{name}] {resp}")
                edu_infos.append(get_educational_info(name))

        doc_id = save_analysis(
            image_blob_path=blob_path,
            object_name=display_name,
            response_text="\n\n".join(all_responses),
            bounding_boxes=all_boxes,
            image_width=padded_image.width,
            image_height=padded_image.height,
            structure_names=structure_names,
            educational_infos=edu_infos,
        )
        return {
            "id": doc_id,
            "object_name": display_name,
            "structure_names": structure_names,
            "response_text": "\n\n".join(all_responses),
            "bounding_boxes": all_boxes,
            "image_url": f"/api/images/{blob_path}",
            "image_width": padded_image.width,
            "image_height": padded_image.height,
            "educational_info": edu_infos[0] if edu_infos else {},
            "educational_infos": edu_infos,
            "mock": False,
        }


@app.get("/api/images/{blob_path:path}")
def proxy_image(blob_path: str):
    """Proxy images from GCS through the backend."""
    from fastapi.responses import Response
    from storage import download_image

    try:
        data = download_image(blob_path)
    except Exception:
        raise HTTPException(404, "Image not found")

    content_type = "image/png"
    if blob_path.endswith(".jpg") or blob_path.endswith(".jpeg"):
        content_type = "image/jpeg"
    return Response(content=data, media_type=content_type)


@app.get("/api/analyses")
def list_all_analyses(limit: int = 20, mock: bool = False):
    """List recent analyses."""
    if mock:
        return _mock_analyses[:limit]
    else:
        try:
            from firestore_db import list_analyses
        except ImportError:
            raise HTTPException(503, "Live mode unavailable: Google Cloud dependencies not installed.")
        analyses = list_analyses(limit=limit)
        for analysis in analyses:
            analysis["image_url"] = f"/api/images/{analysis['image_blob_path']}"
            if "educational_infos" not in analysis:
                names = analysis.get("structure_names") or [s.strip() for s in analysis["object_name"].split(",")]
                analysis["educational_infos"] = [get_educational_info(n) for n in names]
            analysis["educational_info"] = analysis["educational_infos"][0] if analysis.get("educational_infos") else {}
        return analyses


@app.get("/api/analyses/{doc_id}")
def get_single_analysis(doc_id: str, mock: bool = False):
    """Get a specific analysis by ID."""
    if mock:
        for a in _mock_analyses:
            if a["id"] == doc_id:
                return a
        raise HTTPException(404, "Analysis not found")
    else:
        try:
            from firestore_db import get_analysis
        except ImportError:
            raise HTTPException(503, "Live mode unavailable: Google Cloud dependencies not installed.")
        analysis = get_analysis(doc_id)
        if not analysis:
            raise HTTPException(404, "Analysis not found")
        analysis["image_url"] = f"/api/images/{analysis['image_blob_path']}"
        # Reconstruct educational info if not stored
        if "educational_infos" not in analysis:
            names = analysis.get("structure_names") or [s.strip() for s in analysis["object_name"].split(",")]
            analysis["educational_infos"] = [get_educational_info(n) for n in names]
        analysis["educational_info"] = analysis["educational_infos"][0] if analysis.get("educational_infos") else get_educational_info(analysis["object_name"])
        return analysis


@app.delete("/api/analyses/{doc_id}")
def delete_analysis(doc_id: str, mock: bool = False):
    """Delete a specific analysis."""
    if mock:
        global _mock_analyses
        _mock_analyses = [a for a in _mock_analyses if a["id"] != doc_id]
        return {"status": "deleted"}
    else:
        try:
            from firestore_db import delete_analysis as fs_delete
        except ImportError:
            raise HTTPException(503, "Live mode unavailable: Google Cloud dependencies not installed.")
        fs_delete(doc_id)
        return {"status": "deleted"}


@app.delete("/api/analyses")
def delete_all_analyses(mock: bool = False):
    """Delete all analyses."""
    if mock:
        global _mock_analyses
        _mock_analyses = []
        return {"status": "cleared"}
    else:
        try:
            from firestore_db import delete_all_analyses as fs_delete_all
        except ImportError:
            raise HTTPException(503, "Live mode unavailable: Google Cloud dependencies not installed.")
        fs_delete_all()
        return {"status": "cleared"}


ALLOWED_PATCH_FIELDS = {"deep_dive", "findings_report", "chat_messages", "structure_findings"}


@app.patch("/api/analyses/{doc_id}")
async def update_analysis_endpoint(doc_id: str, request: Request, mock: bool = False):
    """Update specific fields on an analysis (deep_dive, findings_report, chat_messages)."""
    body = await request.json()
    updates = {k: v for k, v in body.items() if k in ALLOWED_PATCH_FIELDS}
    if not updates:
        raise HTTPException(400, f"No valid fields. Allowed: {ALLOWED_PATCH_FIELDS}")

    if mock:
        for a in _mock_analyses:
            if a["id"] == doc_id:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                a.update(updates)
                return {"status": "updated", "fields": list(updates.keys())}
        raise HTTPException(404, "Analysis not found")
    else:
        try:
            from firestore_db import update_analysis
        except ImportError:
            raise HTTPException(503, "Live mode unavailable: Google Cloud dependencies not installed.")
        update_analysis(doc_id, updates)
        return {"status": "updated", "fields": list(updates.keys())}


# ===== MedGemma Educational Companion =====


def _load_image_bytes(image_url: str) -> bytes | None:
    """Load image bytes from local uploads or GCS given an image URL path."""
    if not image_url:
        return None
    # Local uploads
    if image_url.startswith("/uploads/"):
        local_path = os.path.join(_LOCAL_UPLOAD_DIR, image_url[len("/uploads/"):])
        if os.path.isfile(local_path):
            with open(local_path, "rb") as f:
                return f.read()
    # GCS proxy path
    if image_url.startswith("/api/images/"):
        blob_path = image_url[len("/api/images/"):]
        try:
            from storage import download_image
            return download_image(blob_path)
        except Exception:
            pass
    return None


@app.post("/api/explain")
async def explain_endpoint(request: Request):
    """Generate an educational explanation using MedGemma."""
    body = await request.json()
    structure_names = body.get("structure_names", [])
    educational_infos = body.get("educational_infos", [])
    level = body.get("level", "medical_student")
    mock = body.get("mock", False)
    image_url = body.get("image_url", "")

    if not structure_names:
        raise HTTPException(400, "structure_names is required")

    if mock:
        from deep_dive import mock_deep_dive
        result = mock_deep_dive(structure_names, level)
    else:
        from deep_dive import generate_deep_dive
        image_bytes = _load_image_bytes(image_url)
        result = generate_deep_dive(image_bytes, structure_names, educational_infos, level)

    return {"explanation": result}


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Multi-turn Q&A chat about the analysis using MedGemma."""
    body = await request.json()
    messages = body.get("messages", [])
    structure_names = body.get("structure_names", [])
    educational_infos = body.get("educational_infos", [])
    mock = body.get("mock", False)
    image_url = body.get("image_url", "")

    if not messages:
        raise HTTPException(400, "messages is required")

    if mock:
        from gemini_flash import mock_chat
        last_msg = messages[-1].get("content", "")
        text = mock_chat(last_msg, structure_names)
    else:
        from vertex_ai import chat_with_medgemma
        image_bytes = _load_image_bytes(image_url)
        text = chat_with_medgemma(messages, image_bytes, structure_names, educational_infos)

    return {"response": text}


@app.post("/api/suggest-questions")
async def suggest_questions_endpoint(request: Request):
    """Generate suggested Q&A questions based on the X-ray and structures."""
    body = await request.json()
    structure_names = body.get("structure_names", [])
    educational_infos = body.get("educational_infos", [])
    mock = body.get("mock", False)
    image_url = body.get("image_url", "")

    if not structure_names:
        raise HTTPException(400, "structure_names is required")

    if mock:
        names = ", ".join(structure_names)
        return {
            "questions": [
                f"Como o(a) {structure_names[0]} aparece neste Raio-X e está dentro dos limites normais?",
                f"Se este paciente tivesse pneumonia, como a aparência do(a) {structure_names[0]} mudaria?",
                "Qual é a relação cardiotorácica nesta imagem e o que ela indica?",
                "Pode me guiar por uma leitura sistemática ABCDE desta radiografia de tórax?",
                f"Quais são as patologias mais comuns que afetam o(a) {names}?",
                "Quais achados sutis um iniciante poderia perder neste Raio-X?",
            ]
        }
    else:
        from vertex_ai import suggest_questions_with_medgemma
        image_bytes = _load_image_bytes(image_url)
        questions = suggest_questions_with_medgemma(image_bytes, structure_names, educational_infos)
        return {"questions": questions}


@app.post("/api/structure-findings")
async def structure_findings_endpoint(request: Request):
    """Extract per-structure observations from MedGemma response text via Gemini Flash."""
    body = await request.json()
    response_text = body.get("response_text", "")
    structure_names = body.get("structure_names", [])
    mock = body.get("mock", False)

    if not structure_names:
        raise HTTPException(400, "structure_names is required")

    if mock:
        from findings_report import mock_structure_findings
        return {"findings": mock_structure_findings(structure_names)}
    else:
        from findings_report import extract_structure_findings
        return {"findings": extract_structure_findings(response_text, structure_names)}


@app.post("/api/findings-report")
async def findings_report_endpoint(request: Request):
    """Generate a comprehensive findings report using MedGemma + Gemini."""
    body = await request.json()
    structure_names = body.get("structure_names", [])
    mock = body.get("mock", False)
    image_url = body.get("image_url", "")

    if mock:
        from findings_report import mock_findings_report
        return mock_findings_report(structure_names)
    else:
        image_bytes = _load_image_bytes(image_url)
        if not image_bytes:
            raise HTTPException(400, "Could not load image for analysis")
        from findings_report import generate_findings_report
        return generate_findings_report(image_bytes, structure_names)


# ===== CT Scan Endpoints =====

# In-memory store for mock CT analyses
_mock_ct_analyses: list[dict] = []

CT_ALLOWED_PATCH_FIELDS = {"deep_dive", "chat_messages"}


@app.get("/api/ct/samples")
def ct_list_samples():
    """List available CT scan sample series."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "body_part": s["body_part"],
            "num_slices": s["num_slices"],
        }
        for s in CT_SAMPLES
    ]


@app.get("/api/ct/frames/{series_id}")
async def ct_get_frames(series_id: str, max_slices: int = 30):
    """Fetch rendered PNG frames for a CT series (for the slice viewer).

    Returns base64-encoded PNG strings sampled evenly across the volume.
    max_slices caps how many frames to return (default 30, max 80).
    """
    sample = next((s for s in CT_SAMPLES if s["id"] == series_id), None)
    if not sample:
        raise HTTPException(400, f"Unknown series_id: {series_id}")

    max_slices = min(max_slices, 80)

    try:
        slices = fetch_rendered_slices(
            sample["study_uid"], sample["series_uid"], max_slices
        )
        return {
            "series_id": series_id,
            "frames": slices,
            "total_instances": sample["total_instances"],
            "num_frames": len(slices),
        }
    except Exception as e:
        logger.error(f"Failed to fetch CT frames: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Failed to fetch CT frames: {str(e)}")


@app.post("/api/ct/analyze")
async def ct_analyze(request: Request):
    """Analyze a CT series. JSON body: {series_id, query, mock}."""
    body = await request.json()
    series_id = body.get("series_id")
    query = body.get("query", "")
    mock = body.get("mock", False)

    if not series_id:
        raise HTTPException(400, "series_id is required")
    if not query.strip():
        raise HTTPException(400, "query is required")

    # Validate series_id
    if not any(s["id"] == series_id for s in CT_SAMPLES):
        raise HTTPException(400, f"Unknown series_id: {series_id}")

    if mock:
        result = mock_ct_analyze(series_id, query)
        _mock_ct_analyses.insert(0, result)
        if len(_mock_ct_analyses) > 50:
            _mock_ct_analyses[:] = _mock_ct_analyses[:50]
        return result
    else:
        try:
            from ct_dicom import analyze_ct
            result = analyze_ct(series_id, query)
            _mock_ct_analyses.insert(0, result)
            return result
        except ImportError:
            raise HTTPException(
                503,
                "Live mode unavailable: Google Cloud dependencies not installed. Use Mock Mode instead.",
            )
        except Exception as e:
            logger.error(f"CT analysis failed: {e}\n{traceback.format_exc()}")
            raise HTTPException(500, f"CT analysis failed: {str(e)}")


@app.get("/api/ct/analyses")
def ct_list_analyses(limit: int = 20):
    """List recent CT analyses (in-memory only)."""
    return _mock_ct_analyses[:limit]


@app.delete("/api/ct/analyses")
def ct_clear_analyses():
    """Clear all CT analyses."""
    global _mock_ct_analyses
    _mock_ct_analyses = []
    return {"status": "cleared"}


@app.get("/api/ct/analyses/{doc_id}")
def ct_get_analysis(doc_id: str):
    """Get a specific CT analysis by ID."""
    for a in _mock_ct_analyses:
        if a["id"] == doc_id:
            return a
    raise HTTPException(404, "CT analysis not found")


@app.delete("/api/ct/analyses/{doc_id}")
def ct_delete_analysis(doc_id: str):
    """Delete a specific CT analysis."""
    global _mock_ct_analyses
    _mock_ct_analyses = [a for a in _mock_ct_analyses if a["id"] != doc_id]
    return {"status": "deleted"}


@app.patch("/api/ct/analyses/{doc_id}")
async def ct_update_analysis(doc_id: str, request: Request):
    """Update fields on a CT analysis (deep_dive, chat_messages)."""
    body = await request.json()
    updates = {k: v for k, v in body.items() if k in CT_ALLOWED_PATCH_FIELDS}
    if not updates:
        raise HTTPException(400, f"No valid fields. Allowed: {CT_ALLOWED_PATCH_FIELDS}")

    for a in _mock_ct_analyses:
        if a["id"] == doc_id:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            a.update(updates)
            return {"status": "updated", "fields": list(updates.keys())}
    raise HTTPException(404, "CT analysis not found")


@app.post("/api/ct/explain")
async def ct_explain_endpoint(request: Request):
    """Generate an educational deep dive for a CT analysis (text-based, no DICOM re-send)."""
    body = await request.json()
    series_name = body.get("series_name", "TC")
    body_part = body.get("body_part", "")
    response_text = body.get("response_text", "")
    level = body.get("level", "medical_student")
    mock = body.get("mock", False)

    if mock:
        from deep_dive import mock_deep_dive
        return {"explanation": mock_deep_dive([f"TC de {body_part}"], level)}
    else:
        from gemini_flash import _call_gemini
        from deep_dive import structure_deep_dive
        try:
            structured = structure_deep_dive(response_text, [f"TC de {body_part}"], level)
            structured["level"] = level
            structured["disclaimer"] = (
                "Esta explicacao e apenas para fins educacionais e nao deve ser "
                "utilizada para diagnostico clinico. Sempre consulte um profissional de saude qualificado."
            )
            return {"explanation": structured}
        except Exception as e:
            logger.error(f"CT explain failed: {e}")
            return {
                "explanation": {
                    "title": f"Deep Dive: TC de {body_part}",
                    "level": level,
                    "sections": [
                        {
                            "id": "content",
                            "title": "Analise",
                            "icon": "clipboard",
                            "content": response_text[:2000],
                            "key_points": [],
                        }
                    ],
                    "disclaimer": "Esta explicacao e apenas para fins educacionais.",
                }
            }


@app.post("/api/ct/chat")
async def ct_chat_endpoint(request: Request):
    """Q&A chat about a CT analysis (text context, no DICOM re-send)."""
    body = await request.json()
    messages = body.get("messages", [])
    series_name = body.get("series_name", "TC")
    body_part = body.get("body_part", "")
    response_text = body.get("response_text", "")
    mock = body.get("mock", False)

    if not messages:
        raise HTTPException(400, "messages is required")

    if mock:
        from gemini_flash import mock_chat
        last_msg = messages[-1].get("content", "")
        text = mock_chat(last_msg, [f"TC de {body_part}"])
        return {"response": text}
    else:
        from gemini_flash import _call_gemini

        system = (
            "Voce e um radiologista especialista em tomografia computadorizada. "
            "Responda perguntas sobre a analise de TC fornecida. "
            "Sempre responda em portugues brasileiro (pt-BR). "
            "Inclua um aviso de que isto e apenas para fins educacionais.\n\n"
            f"Contexto da analise - {series_name} ({body_part}):\n{response_text[:1500]}"
        )

        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        text = _call_gemini(contents, system_instruction=system, max_output_tokens=2048)
        return {"response": text}


@app.post("/api/ct/suggest-questions")
async def ct_suggest_questions_endpoint(request: Request):
    """Generate suggested questions for a CT analysis."""
    body = await request.json()
    body_part = body.get("body_part", "")
    mock = body.get("mock", False)

    questions = [
        f"Quais sao os achados mais importantes nesta TC de {body_part.lower()}?",
        f"A anatomia do(a) {body_part.lower()} esta normal neste exame?",
        "Quais patologias devem ser investigadas com base nestes achados?",
        "Como interpretar sistematicamente uma TC como esta?",
        "Quais sao os diagnosticos diferenciais mais relevantes?",
        "Que exames complementares seriam uteis neste caso?",
    ]
    return {"questions": questions}
