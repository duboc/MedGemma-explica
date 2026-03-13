"""CT Scan analysis module — DICOMweb-based CT series from IDC public data.

Uses rendered PNG frames from the Healthcare API DICOM store, sent as
regular base64 image_url messages to MedGemma.

Architecture note:
  Google's official CT notebook uses the `image_dicom` message type, where
  the model fetches DICOM data directly from a DICOMweb store. Our MedGemma
  endpoint does not support `image_dicom` (returns 400 "Unknown part type"),
  so we use a rendered-frame fallback: download pre-rendered PNGs via the
  DICOMweb /rendered endpoint and send them as standard image_url base64
  parts. This trades off slice count (12 vs 85) and windowing control for
  broader endpoint compatibility. See docs/ct-architecture.md for details.
"""

import base64
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

# Max slices to send to MedGemma (balances detail vs payload size)
MAX_SLICES_FOR_ANALYSIS = 12

# Pre-configured IDC sample series (verified against idc-index + gs://idc-open-data)
# Source: Imaging Data Commons (IDC) public archive
CT_SAMPLES = [
    {
        "id": "chest_ct",
        "name": "CT Torax - LIDC-IDRI",
        "description": "TC de torax do dataset LIDC-IDRI. Serie axial com 133 fatias para avaliacao do parenquima pulmonar.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.298806137288633453246975630178",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.179049373636438705059720603192",
        "body_part": "Torax",
        "num_slices": 133,
        "collection": "lidc_idri",
        "total_instances": 133,
        "default_query": (
            "Analise sistematicamente esta TC de torax. Avalie o parenquima pulmonar, "
            "vias aereas, mediastino, estruturas vasculares e parede toracica. "
            "Descreva os achados, impressao diagnostica e recomendacoes."
        ),
    },
    {
        "id": "abdomen_ct",
        "name": "CT Abdome - KiTS (Rim)",
        "description": "TC de abdome com contraste do dataset C4KC-KiTS. Serie arterial com 80 fatias para avaliacao renal.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.6919.4624.281900760004329249859708333415",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.6919.4624.395226006158762829136614161357",
        "body_part": "Abdome",
        "num_slices": 80,
        "collection": "c4kc_kits",
        "total_instances": 80,
        "default_query": (
            "Analise sistematicamente esta TC de abdome. Avalie os rins, figado, "
            "baco, pancreas, aorta e estruturas retroperitoneais. "
            "Identifique lesoes focais, calcificacoes ou massas e forneca a impressao diagnostica."
        ),
    },
    {
        "id": "head_ct",
        "name": "CT Cranio - CPTAC-AML",
        "description": "TC de cranio sem contraste do dataset CPTAC-AML. Serie coronal com 95 fatias para avaliacao cerebral.",
        "study_uid": "1.3.6.1.4.1.14519.5.2.1.1427.3349.118556328257187014252521570906",
        "series_uid": "1.3.6.1.4.1.14519.5.2.1.1427.3349.154376491757826959383232464810",
        "body_part": "Cranio",
        "num_slices": 95,
        "collection": "cptac_aml",
        "total_instances": 95,
        "default_query": (
            "Analise sistematicamente esta TC de cranio. Avalie o parenquima cerebral, "
            "sistema ventricular, estruturas da fossa posterior, ossos do cranio e "
            "tecidos moles. Identifique assimetrias, lesoes ou desvios da linha media."
        ),
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


def _fetch_instance_sop_uids(study_uid: str, series_uid: str, access_token: str) -> list[str]:
    """Fetch all instance SOP UIDs for a series, sorted by InstanceNumber."""
    import requests

    base = _dicomweb_base_url()
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

    # Extract SOP Instance UIDs
    sop_uids = []
    for inst in instances:
        sop_uid = inst.get("00080018", {}).get("Value", [""])[0]
        if sop_uid:
            sop_uids.append(sop_uid)
    return sop_uids


def _sample_indices(total: int, max_samples: int) -> list[int]:
    """Return evenly spaced indices to sample from a sequence."""
    if total <= max_samples:
        return list(range(total))
    step = total / max_samples
    return [int(i * step) for i in range(max_samples)]


def _fetch_rendered_frame(study_uid: str, series_uid: str, sop_uid: str, access_token: str) -> bytes:
    """Download a rendered PNG frame for a single DICOM instance."""
    import requests

    base = _dicomweb_base_url()
    url = f"{base}/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}/rendered"
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "image/png",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def fetch_rendered_slices(study_uid: str, series_uid: str, max_slices: int = MAX_SLICES_FOR_ANALYSIS) -> list[str]:
    """Fetch evenly-sampled rendered PNG slices as base64 strings.

    Returns list of base64-encoded PNG strings.
    """
    access_token = _get_access_token()

    # Get all instance SOP UIDs sorted by InstanceNumber
    all_sop_uids = _fetch_instance_sop_uids(study_uid, series_uid, access_token)
    if not all_sop_uids:
        raise ValueError("No DICOM instances found for this series")

    # Sample evenly
    indices = _sample_indices(len(all_sop_uids), max_slices)
    sampled_uids = [all_sop_uids[i] for i in indices]

    logger.info(f"Fetching {len(sampled_uids)} rendered slices from {len(all_sop_uids)} total instances")

    # Download rendered frames in parallel
    b64_slices = []

    def _download(sop_uid: str) -> str:
        png_bytes = _fetch_rendered_frame(study_uid, series_uid, sop_uid, access_token)
        return base64.b64encode(png_bytes).decode("utf-8")

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_download, uid): idx for idx, uid in enumerate(sampled_uids)}
        results: dict[int, str] = {}
        for future in futures:
            idx = futures[future]
            results[idx] = future.result()

    # Maintain slice order
    b64_slices = [results[i] for i in range(len(sampled_uids))]

    return b64_slices


def _build_ct_system_prompt() -> str:
    return (
        "Voce e um radiologista especialista em tomografia computadorizada, "
        "atuando como professor em um hospital universitario. "
        "Analise as fatias de TC fornecidas com rigor tecnico e didatico. "
        "As imagens sao fatias representativas amostradas uniformemente ao longo da serie. "
        "Sempre responda em portugues brasileiro (pt-BR). "
        "Use terminologia medica adequada com explicacoes acessiveis. "
        "Inclua um aviso de que esta analise e apenas para fins educacionais."
    )


def _build_ct_query_prompt(query: str, num_slices: int, total_slices: int) -> str:
    return (
        f"Voce esta analisando {num_slices} fatias representativas de uma serie de TC "
        f"com {total_slices} fatias no total, amostradas uniformemente ao longo do volume.\n\n"
        f"Consulta do usuario:\n{query}\n\n"
        f"Forneca uma analise COMPLETA e ESTRUTURADA em portugues brasileiro, "
        f"usando os seguintes cabecalhos em Markdown:\n\n"
        f"## Tecnica\n"
        f"Descreva brevemente o tipo de exame (com/sem contraste, fase, orientacao).\n\n"
        f"## Achados\n"
        f"Descreva sistematicamente todos os achados relevantes, organizados por "
        f"regiao anatomica. Use sub-topicos quando apropriado. Inclua medidas "
        f"estimadas e descricao de densidade/realce quando visiveis.\n\n"
        f"## Impressao Diagnostica\n"
        f"Liste as impressoes principais em ordem de relevancia clinica, numeradas.\n\n"
        f"## Diagnosticos Diferenciais\n"
        f"Para cada achado significativo, liste 2-3 diagnosticos diferenciais.\n\n"
        f"## Correlacao Clinica e Recomendacoes\n"
        f"Sugira correlacao com dados clinicos, exames complementares ou "
        f"acompanhamento quando indicado.\n\n"
        f"> **Aviso**: Esta analise e apenas para fins educacionais e demonstrativos. "
        f"Nao deve ser utilizada para diagnostico clinico real."
    )


def analyze_ct(series_id: str, query: str) -> dict:
    """Analyze a CT series by fetching rendered slices and sending as base64 images."""
    from vertex_ai import _call_medgemma

    sample = next((s for s in CT_SAMPLES if s["id"] == series_id), None)
    if not sample:
        raise ValueError(f"Unknown CT series: {series_id}")

    # Fetch rendered PNG slices as base64
    b64_slices = fetch_rendered_slices(
        sample["study_uid"],
        sample["series_uid"],
        MAX_SLICES_FOR_ANALYSIS,
    )

    if not b64_slices:
        raise ValueError("No rendered slices could be fetched")

    # Build image content parts
    image_parts = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        }
        for b64 in b64_slices
    ]

    prompt_text = _build_ct_query_prompt(query, len(b64_slices), sample["total_instances"])

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": _build_ct_system_prompt()}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                *image_parts,
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
        "num_slices": len(b64_slices),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mock": False,
    }


_MOCK_TEXTS = {
    "chest_ct": """## Tecnica

Tomografia computadorizada de torax sem contraste endovenoso, adquirida em inspiracao profunda, com cortes axiais de 1mm de espessura. Reconstrucoes em janela pulmonar e mediastinal.

## Achados

### Parenquima Pulmonar
- **Pulmao direito**: Parenquima pulmonar com atenuacao preservada nos tres lobos. Nao ha consolidacoes, opacidades em vidro fosco ou nodulos suspeitos. Fissuras integras.
- **Pulmao esquerdo**: Parenquima homogeneo nos lobos superior e inferior. Ausencia de massas ou areas de aprisionamento aereo.
- **Vias aereas**: Traqueia na linha media, com calibre normal. Bronquios principais e lobares pervios, sem espessamento parietal ou impactacao mucoide.

### Mediastino
- **Linfonodos**: Nao ha linfonodomegalias mediastinais ou hilares significativas (< 10mm no menor eixo).
- **Grandes vasos**: Aorta com calibre e trajeto normais. Arteria pulmonar principal sem dilatacao. Veia cava superior e inferior de calibre normal.
- **Coracao**: Silhueta cardiaca de dimensoes normais. Ausencia de derrame pericardico.

### Parede Toracica
- Estruturas osseas sem lesoes liticas ou blasticas. Tecidos moles da parede toracica sem alteracoes.
- Nao ha derrame pleural bilateral.

## Impressao Diagnostica

1. Tomografia computadorizada de torax dentro dos limites da normalidade.
2. Ausencia de nodulos pulmonares, consolidacoes ou massas.
3. Sem linfonodomegalias mediastinais ou hilares.

## Diagnosticos Diferenciais

Nao aplicavel neste caso, pois nao foram identificados achados patologicos significativos.

## Correlacao Clinica e Recomendacoes

- Correlacionar com dados clinicos e indicacao do exame.
- Em pacientes de alto risco para neoplasia pulmonar, considerar acompanhamento conforme protocolos de rastreamento (Lung-RADS).
- Comparar com exames previos quando disponiveis.

> **Aviso**: Esta analise e apenas para fins educacionais e demonstrativos. Nao deve ser utilizada para diagnostico clinico real.""",

    "abdomen_ct": """## Tecnica

Tomografia computadorizada de abdome com contraste endovenoso, adquirida em fase arterial. Cortes axiais de 2.5mm de espessura com reconstrucoes multiplanares.

## Achados

### Rins
- **Rim direito**: Identificada lesao solida no polo inferior do rim direito, com realce heterogeneo na fase arterial, medindo aproximadamente 4.1 x 4.3 cm. Contornos parcialmente irregulares, sem extensao para a gordura perirrenal.
- **Rim esquerdo**: Dimensoes, contornos e atenuacao normais. Boa diferenciacao cortico-medular. Sistema coletor nao dilatado.
- **Calculos**: Presenca de multiplas calcificacoes no grupo calicial inferior do rim direito, compativeis com litiase renal.

### Figado e Vias Biliares
- Figado de dimensoes e contornos normais, com atenuacao homogenea. Ausencia de lesoes focais hepaticas.
- Vesicula biliar normodistendida, sem calculos. Vias biliares intra e extra-hepaticas de calibre normal.

### Baco, Pancreas e Adrenais
- Baco homogeneo, de dimensoes normais.
- Pancreas com morfologia e atenuacao preservadas, sem dilatacao do ducto pancreatico principal.
- Glandulas adrenais de aspecto habitual bilateralmente.

### Estruturas Vasculares e Retroperitonio
- Aorta abdominal de calibre normal, sem aneurismas ou disseccoes.
- Nao ha linfonodomegalias retroperitoneais significativas.

### Parede Abdominal
- Hernia umbilical contendo gordura, sem sinais de encarceramento.

## Impressao Diagnostica

1. **Massa renal direita** (4.1 x 4.3 cm) com realce heterogeneo — altamente suspeita para carcinoma de celulas renais.
2. Litiase renal a direita (multiplos calculos caliciais inferiores).
3. Hernia umbilical contendo gordura, sem complicacoes.

## Diagnosticos Diferenciais

- **Massa renal**: Carcinoma de celulas renais (subtipo de celulas claras), oncocitoma, angiomiolipoma pobre em gordura, metastase renal.
- **Calcificacoes renais**: Litiase por oxalato de calcio, nefrocalcinose focal.

## Correlacao Clinica e Recomendacoes

- Encaminhamento para urologia para avaliacao da massa renal. Considerar nefrectomia parcial vs radical.
- Ressonancia magnetica dos rins para melhor caracterizacao da lesao e planejamento cirurgico.
- Avaliacao laboratorial: funcao renal (creatinina, TFG), hemograma, LDH, calcio.
- TC de torax para estadiamento, caso confirmada neoplasia renal.
- Acompanhamento da litiase renal conforme sintomas.

> **Aviso**: Esta analise e apenas para fins educacionais e demonstrativos. Nao deve ser utilizada para diagnostico clinico real.""",

    "head_ct": """## Tecnica

Tomografia computadorizada de cranio sem contraste endovenoso, adquirida em plano coronal com reconstrucoes multiplanares. Espessura de corte de 2.5mm.

## Achados

### Parenquima Cerebral
- **Hemisferios cerebrais**: Parenquima cerebral com atenuacao normal e simetrica. Diferenciacao entre substancia branca e cinzenta preservada.
- **Fossa posterior**: Cerebelo e tronco encefalico de morfologia e atenuacao normais.
- **Linha media**: Estruturas da linha media centradas, sem desvios. Septo pelucido na posicao habitual.

### Sistema Ventricular
- Ventriculos laterais simetricos, de dimensoes normais para a faixa etaria.
- Terceiro e quarto ventriculos de aspecto habitual, sem sinais de hidrocefalia.
- Cisternas basais pervias.

### Estruturas Extras-axiais
- Espacos subaracnoideos compativeis com a faixa etaria, sem colecoes extras-axiais.
- Ausencia de hematoma subdural, epidural ou hemorragia subaracnoidea.

### Estruturas Osseas
- Calota craniana integra, sem fraturas ou lesoes liticas/blasticas.
- Base do cranio sem alteracoes significativas.
- Seios paranasais e mastoide com pneumatizacao normal.

### Orbitas e Tecidos Moles
- Globos oculares e musculatura extrinseca simetricos.
- Tecidos moles extracranians sem alteracoes.

## Impressao Diagnostica

1. Tomografia computadorizada de cranio sem evidencias de lesoes intracranianas agudas.
2. Ausencia de hemorragias, efeito de massa ou desvio de linha media.
3. Sistema ventricular de dimensoes normais, sem hidrocefalia.

## Diagnosticos Diferenciais

Nao aplicavel neste caso, pois nao foram identificados achados patologicos significativos. Em contexto clinico de cefaleia ou deficit neurologico, considerar:
- Ressonancia magnetica para avaliacao de lesoes de substancia branca
- Angio-TC para avaliacao vascular, se indicada

## Correlacao Clinica e Recomendacoes

- Correlacionar com dados clinicos e exame neurologico.
- Em caso de trauma, reavaliacao em 24-48h se piora clinica.
- Ressonancia magnetica do encefalo indicada para investigacao mais detalhada de queixas neurologicas, quando a TC e normal.
- Considerar angio-TC ou angio-RM se suspeita de patologia vascular.

> **Aviso**: Esta analise e apenas para fins educacionais e demonstrativos. Nao deve ser utilizada para diagnostico clinico real.""",
}


def mock_ct_analyze(series_id: str, query: str) -> dict:
    """Return canned CT analysis for mock/demo mode."""
    sample = next((s for s in CT_SAMPLES if s["id"] == series_id), None)
    if not sample:
        raise ValueError(f"Unknown CT series: {series_id}")

    mock_text = _MOCK_TEXTS.get(series_id, "")

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
