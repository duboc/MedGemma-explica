"""CT Scan analysis module — DICOMweb-based CT series from IDC public data."""

import logging
import uuid
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

# Pre-configured IDC sample series (Google's public DICOM store)
CT_SAMPLES = [
    {
        "id": "liver_lesion",
        "name": "CT Abdome - Lesao Hepatica",
        "description": "TC de abdome com contraste mostrando lesao hepatica focal. Serie axial de fase portal.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.298806137288633453246975630178",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.179049373636438705059720603192",
        "body_part": "Abdome",
        "num_slices": 85,
    },
    {
        "id": "chest_ct",
        "name": "CT Torax - Avaliacao Pulmonar",
        "description": "TC de torax sem contraste para avaliacao do parenquima pulmonar. Serie axial com janela pulmonar.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.511347030803753871132694033474",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357",
        "body_part": "Torax",
        "num_slices": 85,
    },
    {
        "id": "head_ct",
        "name": "CT Cranio - Avaliacao Cerebral",
        "description": "TC de cranio sem contraste para avaliacao de estruturas intracranianas.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.143451261327128179989900675595",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.430109407146633213496148556143",
        "body_part": "Cranio",
        "num_slices": 85,
    },
]


def _dicomweb_base_url() -> str:
    """Build the DICOMweb base URL for the configured DICOM store."""
    return (
        f"https://healthcare.googleapis.com/v1/projects/{settings.dicom_project}/"
        f"locations/{settings.dicom_location}/datasets/{settings.dicom_dataset}/"
        f"dicomStores/{settings.dicom_store}/dicomWeb"
    )


def _get_access_token() -> str:
    """Get a Google Cloud access token for DICOMweb requests."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token


def fetch_dicom_instance_urls(study_uid: str, series_uid: str, max_slices: int = 85) -> tuple[list[str], str]:
    """Fetch instance URLs from DICOMweb, ordered by InstanceNumber, sampled to max_slices.

    Returns (list of DICOMweb instance URLs, access token).
    """
    import requests

    access_token = _get_access_token()
    base = _dicomweb_base_url()

    # Fetch instance metadata to get InstanceNumbers
    metadata_url = f"{base}/studies/{study_uid}/series/{series_uid}/instances"
    resp = requests.get(
        metadata_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/dicom+json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    instances = resp.json()

    # Sort by InstanceNumber (tag 00200013)
    def instance_number(inst: dict) -> int:
        tag = inst.get("00200013", {})
        val = tag.get("Value", [0])
        return int(val[0]) if val else 0

    instances.sort(key=instance_number)

    # Sample evenly if more than max_slices
    if len(instances) > max_slices:
        step = len(instances) / max_slices
        indices = [int(i * step) for i in range(max_slices)]
        instances = [instances[i] for i in indices]

    # Build DICOMweb retrieve URLs
    urls = []
    for inst in instances:
        sop_uid_tag = inst.get("00080018", {})
        sop_uid = sop_uid_tag.get("Value", [""])[0]
        if sop_uid:
            url = f"{base}/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}"
            urls.append(url)

    return urls, access_token


def _build_ct_system_prompt() -> str:
    return (
        "Voce e um radiologista especialista em tomografia computadorizada. "
        "Analise a serie de TC fornecida e responda a consulta do usuario. "
        "Sempre responda em portugues brasileiro (pt-BR). "
        "Inclua um aviso de que esta analise e apenas para fins educacionais."
    )


def _build_ct_query_prompt(query: str) -> str:
    return (
        f"Analise esta serie de tomografia computadorizada e responda:\n\n"
        f"{query}\n\n"
        f"Forneça uma analise detalhada em portugues brasileiro, incluindo:\n"
        f"1. Descricao dos achados principais\n"
        f"2. Impressao diagnostica\n"
        f"3. Correlacao clinica relevante\n"
        f"4. Recomendacoes (se aplicavel)\n\n"
        f"IMPORTANTE: Esta analise e apenas para fins educacionais."
    )


def analyze_ct(series_id: str, query: str) -> dict:
    """Analyze a CT series using MedGemma with image_dicom message type."""
    from vertex_ai import _call_medgemma

    sample = next((s for s in CT_SAMPLES if s["id"] == series_id), None)
    if not sample:
        raise ValueError(f"Unknown CT series: {series_id}")

    # Fetch DICOM instance URLs and auth token
    instance_urls, access_token = fetch_dicom_instance_urls(
        sample["study_uid"], sample["series_uid"], sample["num_slices"]
    )

    if not instance_urls:
        raise ValueError("No DICOM instances found for this series")

    # Build MedGemma message with image_dicom type
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": _build_ct_system_prompt()}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _build_ct_query_prompt(query)},
                {
                    "type": "image_dicom",
                    "image_dicom": {
                        "dicom_web_urls": instance_urls,
                        "dicom_web_auth": {
                            "auth_type": "bearer",
                            "bearer_token": access_token,
                        },
                    },
                },
            ],
        },
    ]

    response_text = _call_medgemma(messages, max_tokens=2048)

    # Clean thinking traces
    if "<end_of_turn>" in response_text:
        response_text = response_text.split("<end_of_turn>", 1)[0]

    for prefix in ["<thought>", "thought"]:
        if response_text.lower().startswith(prefix):
            fa_idx = response_text.find("Final Answer:")
            if fa_idx != -1:
                response_text = response_text[fa_idx + len("Final Answer:"):]
            break

    doc_id = uuid.uuid4().hex
    return {
        "id": doc_id,
        "series_id": series_id,
        "series_name": sample["name"],
        "body_part": sample["body_part"],
        "query": query,
        "response_text": response_text.strip(),
        "num_slices": len(instance_urls),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mock": False,
    }


def mock_ct_analyze(series_id: str, query: str) -> dict:
    """Return canned CT analysis for mock/demo mode."""
    sample = next((s for s in CT_SAMPLES if s["id"] == series_id), None)
    if not sample:
        raise ValueError(f"Unknown CT series: {series_id}")

    body_part = sample["body_part"]
    mock_text = f"""## Analise de Tomografia Computadorizada - {body_part}

### Achados Principais

A serie de TC de {body_part.lower()} foi analisada sistematicamente. Os principais achados incluem:

1. **Avaliacao Geral**: As estruturas anatomicas do(a) {body_part.lower()} apresentam-se dentro dos limites da normalidade em sua maioria.

2. **Parenquima**: O parenquima avaliado apresenta densidade e textura preservadas, sem evidencias de lesoes focais significativas nesta avaliacao demonstrativa.

3. **Estruturas Vasculares**: Os vasos principais apresentam calibre e trajeto normais. Nao ha evidencias de trombose ou dilatacao aneurismatica.

4. **Tecidos Moles**: Os tecidos moles adjacentes apresentam aspecto preservado.

### Impressao Diagnostica

- Estudo tomografico de {body_part.lower()} sem alteracoes significativas nesta demonstracao educacional.
- Os achados sao compativeis com anatomia normal.

### Correlacao Clinica

Esta analise deve ser correlacionada com os dados clinicos e historia do paciente. Estudos adicionais podem ser necessarios dependendo da indicacao clinica.

### Consulta do Usuario

**Pergunta**: {query}

**Resposta**: Com base na analise desta serie de TC, os achados relacionados a sua pergunta sao detalhados acima. Em um contexto clinico real, esta avaliacao seria complementada com comparacao a exames anteriores e correlacao com dados laboratoriais.

> **Aviso**: Esta analise e apenas para fins educacionais e demonstrativos. Nao deve ser utilizada para diagnostico clinico real."""

    doc_id = uuid.uuid4().hex
    return {
        "id": doc_id,
        "series_id": series_id,
        "series_name": sample["name"],
        "body_part": sample["body_part"],
        "query": query,
        "response_text": mock_text,
        "num_slices": sample["num_slices"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mock": True,
    }
