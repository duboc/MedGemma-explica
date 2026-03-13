"""Deep Dive: MedGemma analyzes -> Gemini Flash structures as JSON."""

import json
import logging
import re

logger = logging.getLogger(__name__)

GEMINI_STRUCTURE_PROMPT = """Convert this radiology educational explanation into structured JSON. The input is a raw educational analysis of a chest X-ray for a {level} audience.

INPUT:
{raw_text}

STRUCTURES BEING STUDIED: {structures}

Return ONLY valid JSON matching this exact schema (no markdown fences, no explanation):
{{
  "title": "Educational Deep Dive: [structures]",
  "sections": [
    {{
      "id": "identification",
      "title": "What You're Seeing",
      "icon": "eye",
      "content": "Brief overview paragraph of what these structures look like on this X-ray",
      "key_points": [
        {{
          "term": "structure or concept name",
          "detail": "specific observation or explanation"
        }}
      ]
    }},
    {{
      "id": "normal_vs_abnormal",
      "title": "Normal vs. Abnormal",
      "icon": "balance",
      "comparisons": [
        {{
          "structure": "e.g. Right Lung",
          "normal": "what normal looks like",
          "abnormal_signs": ["sign 1", "sign 2", "sign 3"],
          "this_image": "what this specific image shows"
        }}
      ]
    }},
    {{
      "id": "clinical_connections",
      "title": "Clinical Connections",
      "icon": "stethoscope",
      "connections": [
        {{
          "condition": "e.g. Pneumonia",
          "relevance": "how it relates to these structures",
          "what_to_look_for": "specific X-ray signs"
        }}
      ]
    }},
    {{
      "id": "study_tips",
      "title": "Study Tips",
      "icon": "lightbulb",
      "tips": [
        {{
          "tip": "actionable study tip",
          "why": "why this matters"
        }}
      ]
    }}
  ],
  "disclaimer": "This is for educational purposes only and should not be used for clinical diagnosis."
}}

Rules:
- Extract ALL relevant information from the input text
- Include at least 2-4 key_points in identification
- Include a comparison for each major structure mentioned
- Include at least 3 clinical connections
- Include at least 3 study tips
- Keep text concise but informative
- Be specific to what is described in the input about THIS image
- IMPORTANT: Write ALL text content in Brazilian Portuguese (pt-BR). Keep JSON keys in English."""


def structure_deep_dive(raw_text: str, structure_names: list[str], level: str) -> dict:
    """Send raw MedGemma explanation to Gemini Flash for JSON structuring."""
    from gemini_flash import _call_gemini

    prompt = GEMINI_STRUCTURE_PROMPT.format(
        raw_text=raw_text,
        structures=", ".join(structure_names),
        level=level,
    )
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    response = _call_gemini(
        contents,
        system_instruction="You are a data formatter. Return ONLY valid JSON, no markdown fences, no explanation text.",
        response_mime_type="application/json",
        max_output_tokens=4096,
    )

    # Extract JSON from response
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        response = response[start:end]

    return json.loads(response)


def generate_deep_dive(
    image_bytes: bytes | None,
    structure_names: list[str],
    educational_infos: list[dict],
    level: str = "medical_student",
) -> dict:
    """Two-step pipeline: MedGemma explains -> Gemini structures as JSON."""
    from vertex_ai import explain_with_medgemma

    # Step 1: MedGemma generates raw educational text
    raw_text = explain_with_medgemma(image_bytes, structure_names, educational_infos, level)
    logger.info(f"MedGemma deep dive raw output: {len(raw_text)} chars")

    # Step 2: Gemini Flash structures into JSON
    try:
        structured = structure_deep_dive(raw_text, structure_names, level)
        structured["level"] = level
        structured["disclaimer"] = (
            "Esta explicação é apenas para fins educacionais e não deve ser "
            "utilizada para diagnóstico clínico. Sempre consulte um profissional de saúde qualificado."
        )
        return structured
    except Exception as e:
        logger.error(f"Gemini structuring failed for deep dive: {e}")
        # Fallback: return a minimal structure with raw text
        return {
            "title": f"Deep Dive: {', '.join(structure_names)}",
            "level": level,
            "sections": [
                {
                    "id": "content",
                    "title": "Análise",
                    "icon": "clipboard",
                    "content": raw_text[:2000],
                    "key_points": [],
                }
            ],
            "disclaimer": "Esta explicação é apenas para fins educacionais.",
        }


def mock_deep_dive(structure_names: list[str], level: str = "medical_student") -> dict:
    """Return a realistic mock deep dive for UI testing."""
    names = ", ".join(structure_names)
    first = structure_names[0] if structure_names else "estruturas torácicas"

    return {
        "title": f"Deep Dive Educacional: {names}",
        "level": level,
        "sections": [
            {
                "id": "identification",
                "title": "O Que Você Está Vendo",
                "icon": "eye",
                "content": f"Nesta radiografia de tórax, o MedGemma identificou e localizou o(a) {names}. Estas estruturas são marcos fundamentais na interpretação de radiografias de tórax que todo profissional médico deve ser capaz de identificar com confiança.",
                "key_points": [
                    {
                        "term": first.title(),
                        "detail": f"O(A) {first} é claramente visível na posição anatômica esperada. Em uma incidência PA bem posicionada, deve aparecer simétrico(a) com seu correspondente contralateral (quando aplicável).",
                    },
                    {
                        "term": "Densidade Radiográfica",
                        "detail": "Diferentes tecidos absorvem raios-X de maneiras distintas: ar (preto), gordura (cinza escuro), tecido mole/líquido (cinza claro), osso/cálcio (branco), metal (branco brilhante).",
                    },
                    {
                        "term": "Marcos Anatômicos",
                        "detail": "Use as estruturas ao redor como pontos de referência. A carina, o arco aórtico e os hemidiafragmas são marcos confiáveis para orientação.",
                    },
                    {
                        "term": "Qualidade da Imagem",
                        "detail": "Antes de interpretar, verifique: PA vs AP, rotação (simetria das clavículas), penetração (vértebras visíveis através do coração), inspiração (6+ costelas anteriores).",
                    },
                ],
            },
            {
                "id": "normal_vs_abnormal",
                "title": "Normal vs. Anormal",
                "icon": "balance",
                "comparisons": [
                    {
                        "structure": first.title(),
                        "normal": f"O(A) {first} aparece na posição esperada com tamanho, forma e densidade normais. As bordas são bem definidas.",
                        "abnormal_signs": [
                            "Aumento ou diminuição da densidade",
                            "Desvio da posição normal",
                            "Perda das bordas normais (sinal da silhueta)",
                            "Mudança inesperada de tamanho",
                        ],
                        "this_image": f"O(A) {first} aparece dentro dos limites normais nesta imagem, sem sinais de patologia aguda.",
                    },
                    {
                        "structure": "Avaliação Geral",
                        "normal": "Campos pulmonares simétricos, silhueta cardíaca normal (ICT < 0,5), ângulos costofrênicos agudos, traqueia na linha média.",
                        "abnormal_signs": [
                            "Opacidade pulmonar assimétrica",
                            "Mediastino alargado",
                            "Velamento dos ângulos costofrênicos",
                            "Desvio traqueal",
                        ],
                        "this_image": "A aparência geral do tórax é normal, sem achados agudos.",
                    },
                ],
            },
            {
                "id": "clinical_connections",
                "title": "Conexões Clínicas",
                "icon": "stethoscope",
                "connections": [
                    {
                        "condition": "Pneumonia",
                        "relevance": f"A infecção pode causar consolidação adjacente ou dentro do(a) {first}, aparecendo como opacidade aumentada com possíveis broncogramas aéreos.",
                        "what_to_look_for": "Consolidação focal, broncogramas aéreos, sinal da silhueta, derrame parapneumônico",
                    },
                    {
                        "condition": "Insuficiência Cardíaca",
                        "relevance": "A sobrecarga hídrica manifesta-se como cardiomegalia, cefalização dos vasos, linhas B de Kerley e derrames bilaterais.",
                        "what_to_look_for": "ICT > 0,5, distensão dos vasos do lobo superior, nebulosidade peri-hilar, derrames pleurais bilaterais",
                    },
                    {
                        "condition": "Pneumotórax",
                        "relevance": "Ar no espaço pleural causa colapso pulmonar. A linha pleural visceral torna-se visível com ausência de marcas pulmonares na periferia.",
                        "what_to_look_for": "Linha pleural visceral, ausência de marcas pulmonares periféricas, sinal do sulco profundo (decúbito), desvio mediastinal (tensão)",
                    },
                ],
            },
            {
                "id": "study_tips",
                "title": "Dicas de Estudo",
                "icon": "lightbulb",
                "tips": [
                    {
                        "tip": "Use a abordagem sistemática ABCDE",
                        "why": "Vias Aéreas, Bones (Ossos), Cardíaco, Diafragma, Everything else (Todo o resto) — garante que você nunca perca um achado sendo metódico.",
                    },
                    {
                        "tip": "Sempre compare com o lado contralateral",
                        "why": "A assimetria é frequentemente a primeira pista de patologia. Treine seu olho para detectar diferenças sutis entre esquerda e direita.",
                    },
                    {
                        "tip": "Verifique as bordas e cantos",
                        "why": "Ápices, ângulos costofrênicos e espaço retrocardíaco são 'pontos cegos' comuns onde achados são perdidos.",
                    },
                    {
                        "tip": "Conheça seus tubos e cateteres",
                        "why": "Na prática clínica, confirmar o posicionamento correto de tubos endotraqueais, cateteres centrais e drenos torácicos é uma habilidade crítica.",
                    },
                ],
            },
        ],
        "disclaimer": "Esta explicação é apenas para fins educacionais e não deve ser utilizada para diagnóstico clínico. Sempre consulte um profissional de saúde qualificado.",
    }
