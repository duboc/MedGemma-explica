"""
Experiment: Can MedGemma respond properly in Brazilian Portuguese?

Tests three use cases against a sample chest X-ray:
  1. Image analysis with bounding box localization (pt-BR prompt)
  2. Educational explanation (pt-BR prompt)
  3. Q&A chat (pt-BR question)

Usage:
  cd experiments
  python pt_br_medgemma_test.py [--image PATH]

Requires:
  - gcloud auth application-default login
  - Access to the MedGemma endpoint configured in backend/config.py
"""

import base64
import json
import os
import re
import sys
import time

# Add backend to path so we can reuse config and the MedGemma caller
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_image(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def call_medgemma(messages: list[dict], max_tokens: int = 2048) -> str:
    """Call MedGemma endpoint (copied from vertex_ai to keep experiment self-contained)."""
    import google.auth
    import google.auth.transport.requests
    import requests

    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)

    url = (
        f"{settings.medgemma_endpoint_url}/v1/projects/"
        f"{settings.medgemma_endpoint_project}/locations/{settings.location}/"
        f"endpoints/{settings.medgemma_endpoint_id}:predict"
    )

    payload = {
        "instances": [
            {
                "@requestFormat": "chatCompletions",
                "messages": messages,
                "max_tokens": max_tokens,
            }
        ]
    }

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    resp.raise_for_status()

    result = resp.json()
    predictions = result.get("predictions", {})
    if isinstance(predictions, dict):
        choices = predictions.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", str(predictions))
        return str(predictions)
    elif isinstance(predictions, list) and predictions:
        prediction = predictions[0]
        if isinstance(prediction, dict):
            choices = prediction.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", str(prediction))
            return str(prediction)
        return str(prediction)
    return str(result)


def clean_response(text: str) -> str:
    """Strip MedGemma thinking traces."""
    if "<end_of_turn>" in text:
        text = text.split("<end_of_turn>", 1)[0]
    # Remove <thought>...</thought> blocks
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Handle unclosed thought tags
    for prefix in ["<thought>", "thought"]:
        if text.strip().lower().startswith(prefix):
            fa_idx = text.find("Final Answer:")
            if fa_idx != -1:
                text = text[fa_idx + len("Final Answer:"):]
            break
    return text.strip()


def detect_language(text: str) -> dict:
    """Simple heuristic to check if response is in Portuguese."""
    pt_markers = [
        "pulmão", "pulmao", "coração", "coracao", "tórax", "torax",
        "radiografia", "estrutura", "anatomia", "clínica", "clinica",
        "observação", "observacao", "diagnóstico", "diagnostico",
        "achados", "análise", "analise", "imagem", "normal",
        "anormal", "educacional", "médico", "medico", "paciente",
        "é ", "são ", "está ", "não ", "nao ", "uma ", "este ",
        "esta ", "como ", "para ", "que ", "dos ", "das ", "nos ",
        "nas ", "pelo ", "pela ", " ou ", " com ", " sem ",
    ]
    text_lower = text.lower()
    matches = [m for m in pt_markers if m in text_lower]
    score = len(matches)
    is_pt = score >= 5
    return {
        "likely_portuguese": is_pt,
        "marker_count": score,
        "markers_found": matches[:10],
    }


def print_section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_result(label: str, value: str, max_chars: int = 1500):
    display = value[:max_chars] + ("..." if len(value) > max_chars else "")
    print(f"--- {label} ---")
    print(display)
    print()


# ---------------------------------------------------------------------------
# Test 1: Localization with pt-BR prompt
# ---------------------------------------------------------------------------

def test_localization_ptbr(image_b64: str) -> dict:
    """Test bounding box localization with Portuguese prompt."""
    print_section("TESTE 1: Localização com prompt em pt-BR")

    prompt = """Instruções:
A consulta do usuário a seguir exigirá a saída de caixas delimitadoras (bounding boxes). O formato das coordenadas é [y0, x0, y1, x1] onde (y0, x0) é o canto superior esquerdo e (y1, x1) é o canto inferior direito. Normalize as coordenadas x e y no intervalo [0, 1000]. Você DEVE retornar uma lista JSON de objetos entre ```json...```, por exemplo ```json[{"box_2d": [800, 3, 840, 471], "label": "coração"}]```.

Lembre-se: "esquerdo" refere-se ao lado esquerdo do paciente.

Consulta:
Onde estão o coração e os pulmões nesta radiografia de tórax? Raciocine antes de dar a resposta final. Retorne a resposta final no formato "Final Answer: X" onde X é a lista JSON. Responda em português brasileiro."""

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Você é um radiologista especialista. Responda sempre em português brasileiro."}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        },
    ]

    start = time.time()
    raw = call_medgemma(messages, max_tokens=2048)
    elapsed = time.time() - start

    cleaned = clean_response(raw)
    lang = detect_language(cleaned)

    # Try to extract bounding boxes
    boxes = []
    json_matches = re.findall(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    for match in reversed(json_matches):
        try:
            boxes = json.loads(match)
            break
        except json.JSONDecodeError:
            continue

    print_result("Resposta bruta (raw)", raw)
    print(f"Tempo de resposta: {elapsed:.1f}s")
    print(f"Bounding boxes encontradas: {len(boxes)}")
    if boxes:
        for b in boxes:
            print(f"  - {b.get('label', '?')}: {b.get('box_2d', '?')}")
    print(f"Detecção de idioma: {lang}")

    return {
        "test": "localization_ptbr",
        "elapsed_s": round(elapsed, 1),
        "boxes_found": len(boxes),
        "boxes": boxes,
        "language": lang,
        "response_length": len(raw),
        "labels_in_portuguese": any(
            any(c in b.get("label", "").lower() for c in ["coração", "coracao", "pulmão", "pulmao", "esquerdo", "direito"])
            for b in boxes
        ),
    }


# ---------------------------------------------------------------------------
# Test 2: Educational explanation in pt-BR
# ---------------------------------------------------------------------------

def test_explanation_ptbr(image_b64: str) -> dict:
    """Test educational explanation in Portuguese."""
    print_section("TESTE 2: Explicação educacional em pt-BR")

    prompt = """Você analisou esta radiografia de tórax e identificou as seguintes estruturas anatômicas:

- Coração: A silhueta cardíaca em uma radiografia PA normalmente ocupa menos de 50% da largura torácica.
- Pulmão direito: O pulmão direito tem três lobos e é ligeiramente maior que o esquerdo.
- Pulmão esquerdo: O pulmão esquerdo tem dois lobos e é ligeiramente menor para acomodar o coração.

Por favor, forneça uma explicação educacional abrangente para um estudante de medicina. Inclua:

1. **O que você está vendo**: Explique como essas estruturas aparecem nesta radiografia.
2. **Normal vs. Anormal**: Descreva a aparência normal e sinais que indicam patologia.
3. **Conexões Clínicas**: Como essas estruturas se relacionam com condições clínicas comuns?
4. **Dicas de Estudo**: Pontos-chave para identificar essas estruturas em radiografias.

Responda inteiramente em português brasileiro."""

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Você é um educador médico especialista em radiologia e anatomia. Responda sempre em português brasileiro."}],
        },
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ]},
    ]

    start = time.time()
    raw = call_medgemma(messages, max_tokens=2048)
    elapsed = time.time() - start

    cleaned = clean_response(raw)
    lang = detect_language(cleaned)

    # Check if the 4 requested sections appear in Portuguese
    section_markers = {
        "o_que_voce_ve": ["o que você está vendo", "o que voce esta vendo", "o que se vê", "identificação"],
        "normal_anormal": ["normal vs", "normal versus", "anormal", "patologia"],
        "conexoes_clinicas": ["conexões clínicas", "conexoes clinicas", "condições clínicas", "clinica"],
        "dicas_estudo": ["dicas de estudo", "dicas", "pontos-chave", "lembr"],
    }

    sections_found = {}
    for key, markers in section_markers.items():
        sections_found[key] = any(m in cleaned.lower() for m in markers)

    print_result("Resposta limpa", cleaned)
    print(f"Tempo de resposta: {elapsed:.1f}s")
    print(f"Detecção de idioma: {lang}")
    print(f"Seções encontradas: {sections_found}")

    return {
        "test": "explanation_ptbr",
        "elapsed_s": round(elapsed, 1),
        "language": lang,
        "sections_found": sections_found,
        "all_sections_present": all(sections_found.values()),
        "response_length": len(cleaned),
    }


# ---------------------------------------------------------------------------
# Test 3: Q&A chat in pt-BR
# ---------------------------------------------------------------------------

def test_chat_ptbr(image_b64: str) -> dict:
    """Test Q&A conversation in Portuguese."""
    print_section("TESTE 3: Chat Q&A em pt-BR")

    system_text = (
        "Você é um educador médico especialista em radiologia e anatomia. "
        "Você ajuda estudantes a entender achados em radiografias de tórax.\n\n"
        "A análise atual envolve estas estruturas:\n"
        "- Coração: A silhueta cardíaca normalmente ocupa menos de 50% da largura torácica.\n"
        "- Pulmão direito: Três lobos, ligeiramente maior que o esquerdo.\n"
        "- Pulmão esquerdo: Dois lobos, menor para acomodar o coração.\n\n"
        "Responda às perguntas sobre estas estruturas em português brasileiro. "
        "Inclua sempre um aviso de que isto é apenas para fins educacionais."
    )

    question = (
        "Se este paciente tivesse pneumonia no lobo inferior direito, "
        "como a radiografia mudaria? Quais sinais eu deveria procurar?"
    )

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_text}],
        },
        {"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ]},
    ]

    start = time.time()
    raw = call_medgemma(messages, max_tokens=2048)
    elapsed = time.time() - start

    cleaned = clean_response(raw)
    lang = detect_language(cleaned)

    # Check for key medical terms in Portuguese
    medical_terms_pt = [
        "consolidação", "consolidacao", "opacidade", "broncograma",
        "infiltrado", "pneumonia", "lobo inferior", "derrame",
        "silhueta", "radiopac",
    ]
    terms_found = [t for t in medical_terms_pt if t in cleaned.lower()]

    print_result("Resposta limpa", cleaned)
    print(f"Tempo de resposta: {elapsed:.1f}s")
    print(f"Detecção de idioma: {lang}")
    print(f"Termos médicos em pt-BR: {terms_found}")

    return {
        "test": "chat_ptbr",
        "elapsed_s": round(elapsed, 1),
        "language": lang,
        "medical_terms_pt_found": terms_found,
        "response_length": len(cleaned),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test MedGemma Portuguese responses")
    parser.add_argument(
        "--image",
        default=os.path.join(os.path.dirname(__file__), "..", "sample-xrays", "openi_normal_cxr_1.png"),
        help="Path to chest X-ray image",
    )
    args = parser.parse_args()

    image_path = os.path.abspath(args.image)
    print(f"Image: {image_path}")
    print(f"Endpoint: {settings.medgemma_endpoint_id}")
    print(f"Project:  {settings.medgemma_endpoint_project}")

    image_bytes = load_image(image_path)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    results = []

    # Run all three tests
    results.append(test_localization_ptbr(image_b64))
    results.append(test_explanation_ptbr(image_b64))
    results.append(test_chat_ptbr(image_b64))

    # Summary
    print_section("RESUMO DOS RESULTADOS")

    for r in results:
        test_name = r["test"]
        is_pt = r["language"]["likely_portuguese"]
        marker_count = r["language"]["marker_count"]
        elapsed = r["elapsed_s"]
        status = "PORTUGUES" if is_pt else "INGLES/MISTO"
        print(f"  {test_name:25s}  idioma={status:15s}  marcadores={marker_count:2d}  tempo={elapsed:.1f}s")

        if test_name == "localization_ptbr":
            labels_pt = r.get("labels_in_portuguese", False)
            print(f"    -> boxes={r['boxes_found']}  labels_em_pt={labels_pt}")
        elif test_name == "explanation_ptbr":
            print(f"    -> todas_secoes={r['all_sections_present']}  secoes={r['sections_found']}")
        elif test_name == "chat_ptbr":
            print(f"    -> termos_medicos_pt={r['medical_terms_pt_found']}")

    # Save JSON results
    output_path = os.path.join(os.path.dirname(__file__), "pt_br_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
