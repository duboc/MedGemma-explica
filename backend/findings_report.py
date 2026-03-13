"""Findings Report: MedGemma analyzes → Gemini Flash structures as JSON."""

import base64
import json
import logging
import re

logger = logging.getLogger(__name__)

# Single comprehensive prompt for MedGemma
MEDGEMMA_PROMPT = """Analyze this chest X-ray image comprehensively. Cover ALL of the following:

1. OVERALL ASSESSMENT: For each visible structure (heart, both lungs, mediastinum, diaphragm, costophrenic angles, bones), state if it appears normal/abnormal/borderline with specific findings. Estimate the cardiothoracic ratio.

2. SYSTEMATIC ABCDE READING:
   A-Airway, B-Bones, C-Cardiac, D-Diaphragm, E-Everything else.
   For each, describe what you observe on this image.

3. PATHOLOGY SCENARIOS: For each condition below, explain what would change on THIS image if the patient had it, and list the key X-ray signs:
   - Pneumonia (lobar vs bronchopneumonia)
   - Heart failure / cardiomegaly
   - Pleural effusion
   - Pneumothorax

4. CLINICAL PEARLS: Normal findings to appreciate, key measurements, common interpretation pitfalls, and what additional imaging might help.

Be thorough and specific to THIS image.

IMPORTANT: Write your entire response in Brazilian Portuguese (pt-BR)."""

# Gemini prompt to structure MedGemma's raw output into JSON
GEMINI_STRUCTURE_PROMPT = """Convert this radiology analysis into structured JSON. The input is a raw analysis of a chest X-ray.

INPUT:
{raw_text}

Return ONLY valid JSON matching this exact schema (no markdown fences, no explanation):
{{
  "overall_assessment": {{
    "summary": "1-2 sentence overall impression of this X-ray",
    "findings": [
      {{
        "structure": "e.g. Heart",
        "status": "normal|abnormal|borderline",
        "finding": "Brief one-line finding",
        "detail": "Supporting detail with measurements if available"
      }}
    ]
  }},
  "systematic_approach": [
    {{
      "step": "e.g. A - Airway",
      "checks": ["what to check item 1", "item 2"],
      "observation": "what is observed on this specific image"
    }}
  ],
  "pathology_scenarios": [
    {{
      "condition": "e.g. Pneumonia",
      "icon": "emoji for this condition",
      "current_status": "what this image currently shows for this condition",
      "what_would_change": "how image would look if patient had this condition",
      "key_signs": ["sign 1", "sign 2", "sign 3"],
      "teaching_point": "important educational note about this condition on X-ray"
    }}
  ],
  "clinical_pearls": [
    {{
      "category": "e.g. Normal Findings | Key Measurements | Common Pitfalls | Next Steps",
      "icon": "emoji",
      "items": [
        {{
          "title": "pearl title",
          "detail": "explanation"
        }}
      ]
    }}
  ]
}}

Rules:
- Extract ALL findings and observations from the input text
- Include at least 4-6 findings in overall_assessment
- Include all 5 ABCDE steps in systematic_approach
- Include at least 4 pathology scenarios
- Include at least 3 clinical pearl categories
- Use appropriate medical emojis for icons
- Keep text concise but informative
- IMPORTANT: Write ALL text content values in Brazilian Portuguese (pt-BR). Keep JSON keys in English."""


def generate_findings_report(image_bytes: bytes, structure_names: list[str]) -> dict:
    """Two-step pipeline: MedGemma analyzes image → Gemini structures as JSON."""
    from vertex_ai import _call_medgemma
    from gemini_flash import _call_gemini

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    context = ""
    if structure_names:
        context = f"\nThe user is specifically studying: {', '.join(structure_names)}. Pay extra attention to these structures.\n"

    # Step 1: MedGemma analyzes the image
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are an expert radiologist and medical educator. Provide thorough, accurate analysis."}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": MEDGEMMA_PROMPT + context},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        },
    ]

    try:
        raw_text = _call_medgemma(messages, max_tokens=4096)
        if "<end_of_turn>" in raw_text:
            raw_text = raw_text.split("<end_of_turn>", 1)[0]
        for prefix in ["<thought>", "thought"]:
            if raw_text.lower().startswith(prefix):
                fa_idx = raw_text.find("Final Answer:")
                if fa_idx != -1:
                    raw_text = raw_text[fa_idx + len("Final Answer:"):]
                break
    except Exception as e:
        logger.error(f"MedGemma analysis failed: {e}")
        raise

    logger.info(f"MedGemma raw output: {len(raw_text)} chars")

    # Step 2: Gemini Flash structures into JSON
    try:
        structured = _parse_with_gemini(raw_text)
        structured["disclaimer"] = (
            "Esta análise é apenas para fins educacionais e não deve ser considerada "
            "um substituto para aconselhamento médico profissional. Sempre consulte um "
            "profissional de saúde qualificado para tomada de decisões clínicas."
        )
        return structured
    except Exception as e:
        logger.error(f"Gemini structuring failed: {e}")
        # Fallback: parse raw text into basic sections
        return _build_fallback_report(raw_text)


def _parse_with_gemini(raw_text: str) -> dict:
    """Send raw analysis text to Gemini Flash for JSON structuring."""
    from gemini_flash import _call_gemini

    prompt = GEMINI_STRUCTURE_PROMPT.format(raw_text=raw_text)
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    response = _call_gemini(
        contents,
        system_instruction="You are a data formatter. Return ONLY valid JSON, no markdown fences, no explanation text.",
        response_mime_type="application/json",
        max_output_tokens=4096,
    )

    # Even with JSON mode, extract conservatively in case of wrapping
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        response = response[start:end]

    return json.loads(response)


def _build_fallback_report(raw_text: str) -> dict:
    """Build a structured report from raw text when Gemini JSON parsing fails."""
    # Try to extract meaningful sections from the raw text
    findings = []
    structures = ["Heart", "Right Lung", "Left Lung", "Mediastinum", "Diaphragm", "Bones"]
    for struct in structures:
        # Search for mentions of this structure in the raw text
        pattern = re.compile(rf"(?i)\b{struct}\b[:\s]*(.*?)(?:\n\n|\n[A-Z]|\Z)", re.DOTALL)
        match = pattern.search(raw_text)
        detail = match.group(1).strip()[:200] if match else "Not specifically mentioned in analysis."
        findings.append({
            "structure": struct,
            "status": "normal",
            "finding": f"{struct} assessment from MedGemma analysis",
            "detail": detail,
        })

    # Build a summary from the first paragraph or first ~200 chars
    summary_text = raw_text.strip().split("\n\n")[0][:300] if raw_text.strip() else "Analysis completed."

    return {
        "overall_assessment": {
            "summary": summary_text,
            "findings": findings,
        },
        "systematic_approach": [
            {"step": "Full Analysis", "checks": ["See raw text below"], "observation": raw_text[:500]},
        ],
        "pathology_scenarios": [],
        "clinical_pearls": [],
        "raw_text": raw_text,
        "disclaimer": "Esta análise é apenas para fins educacionais. A estruturação pelo Gemini não estava disponível; mostrando achados extraídos.",
    }


STRUCTURE_FINDINGS_PROMPT = """Extract per-structure observations from this MedGemma analysis of a chest X-ray.

ANALYSIS TEXT:
{raw_text}

STRUCTURES TO EXTRACT: {structures}

Return ONLY valid JSON matching this schema (no markdown, no explanation):
{{
  "findings": [
    {{
      "name": "structure name (lowercase)",
      "appearance": "what the structure looks like on this specific image",
      "status": "normal|abnormal|borderline",
      "notable": "any notable observations specific to this image",
      "clinical_note": "relevant clinical context for this structure"
    }}
  ]
}}

Rules:
- Include one entry per structure in the STRUCTURES list
- Base observations on what the analysis text ACTUALLY says about this image
- If the analysis doesn't mention a structure, describe its expected appearance
- status should reflect what was observed on THIS image
- IMPORTANT: Write ALL text content values in Brazilian Portuguese (pt-BR). Keep JSON keys in English."""


def extract_structure_findings(raw_text: str, structure_names: list[str]) -> list[dict]:
    """Use Gemini Flash to extract per-structure findings from MedGemma response."""
    from gemini_flash import _call_gemini

    prompt = STRUCTURE_FINDINGS_PROMPT.format(
        raw_text=raw_text,
        structures=", ".join(structure_names),
    )
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    response = _call_gemini(
        contents,
        system_instruction="You are a data formatter. Return ONLY valid JSON.",
        response_mime_type="application/json",
    )

    # Extract JSON conservatively
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        response = response[start:end]

    try:
        data = json.loads(response)
        return data.get("findings", [])
    except (json.JSONDecodeError, AttributeError):
        logger.error("Failed to parse structure findings JSON")
        return [
            {"name": n, "appearance": "Análise disponível", "status": "normal", "notable": "", "clinical_note": ""}
            for n in structure_names
        ]


def mock_structure_findings(structure_names: list[str]) -> list[dict]:
    """Return mock per-structure findings for UI testing."""
    mock_data = {
        "right lung": {
            "appearance": "Campo pulmonar claro com marcas broncovasculares normais estendendo-se até a periferia",
            "status": "normal",
            "notable": "Sem consolidação focal, massa ou derrame pleural. Ângulo costofrênico direito agudo.",
            "clinical_note": "O brônquio principal direito é mais largo e mais vertical, tornando-o o local mais comum para corpos estranhos aspirados.",
        },
        "left lung": {
            "appearance": "Campo pulmonar claro, parcialmente obscurecido pela silhueta cardíaca na região retrocardíaca",
            "status": "normal",
            "notable": "Sem consolidação ou derrame. A língula e o lobo inferior esquerdo parecem claros.",
            "clinical_note": "Sempre verifique o espaço retrocardíaco cuidadosamente - pneumonia do lobo inferior esquerdo pode se esconder atrás do coração.",
        },
        "heart": {
            "appearance": "Silhueta cardíaca com bordas bem definidas, RCT aproximadamente 0,48-0,50",
            "status": "borderline",
            "notable": "Tamanho cardíaco limítrofe no limite superior do normal. Borda cardíaca esquerda levemente proeminente.",
            "clinical_note": "RCT > 0,5 em um filme PA sugere cardiomegalia. Filmes AP aumentam o coração em ~20%, então sempre confirme o posicionamento PA.",
        },
        "trachea": {
            "appearance": "Estrutura tubular cheia de ar na linha média do mediastino superior",
            "status": "normal",
            "notable": "Posição na linha média sem desvio. Carina aproximadamente no nível T4-T5.",
            "clinical_note": "Desvio traqueal pode indicar pneumotórax hipertensivo (afastando-se do lado afetado) ou atelectasia (em direção ao lado afetado).",
        },
        "aortic arch": {
            "appearance": "Opacidade arredondada visível no lado esquerdo do mediastino acima do hilo esquerdo",
            "status": "normal",
            "notable": "Calibre normal sem desdobramento ou calcificação visível.",
            "clinical_note": "Um mediastino alargado (>8cm) pode sugerir dissecção aórtica ou aneurisma - meça cuidadosamente.",
        },
    }

    results = []
    for name in structure_names:
        normalized = name.lower().strip()
        if normalized in mock_data:
            results.append({"name": normalized, **mock_data[normalized]})
        else:
            results.append({
                "name": normalized,
                "appearance": f"O {name} é visível em sua posição anatômica esperada",
                "status": "normal",
                "notable": "Nenhuma anormalidade aguda identificada.",
                "clinical_note": f"O {name} é um marco importante na interpretação sistemática de radiografia de tórax.",
            })
    return results


def mock_findings_report(structure_names: list[str]) -> dict:
    """Return a realistic mock findings report for UI testing."""
    names = ", ".join(structure_names) if structure_names else "estruturas torácicas"
    return {
        "overall_assessment": {
            "summary": f"Radiografia de tórax PA demonstra anatomia cardiopulmonar geralmente normal com foco em {names}. Nenhum processo cardiopulmonar agudo identificado.",
            "findings": [
                {
                    "structure": "Heart",
                    "status": "borderline",
                    "finding": "Tamanho limítrofe da silhueta cardíaca",
                    "detail": "Índice cardiotorácico (ICT) aproximadamente 0,48-0,50, no limite superior da normalidade. Borda cardíaca esquerda levemente proeminente.",
                },
                {
                    "structure": "Right Lung",
                    "status": "normal",
                    "finding": "Campo pulmonar limpo",
                    "detail": "Bem aerado, sem consolidação focal, massa ou derrame pleural. Marcas broncovasculares normais por todo o pulmão.",
                },
                {
                    "structure": "Left Lung",
                    "status": "normal",
                    "finding": "Campo pulmonar limpo",
                    "detail": "Campo pulmonar esquerdo aparenta estar limpo. A silhueta cardíaca obscurece parcialmente a região retrocardíaca, mas nenhuma anormalidade óbvia identificada.",
                },
                {
                    "structure": "Mediastinum",
                    "status": "normal",
                    "finding": "Centralizado, não alargado",
                    "detail": "O mediastino está centralizado e não alargado. O arco aórtico está dentro dos limites normais.",
                },
                {
                    "structure": "Diaphragm",
                    "status": "normal",
                    "finding": "Hemidiafragmas lisos e bem definidos",
                    "detail": "Hemidiafragma direito discretamente mais elevado que o esquerdo (normal). Ângulos costofrênicos agudos bilateralmente.",
                },
                {
                    "structure": "Bones",
                    "status": "normal",
                    "finding": "Sem fraturas ou lesões",
                    "detail": "Clavículas, costelas e coluna torácica visíveis não mostram fraturas ou lesões líticas. Clavículas simétricas confirmam bom posicionamento.",
                },
            ],
        },
        "systematic_approach": [
            {
                "step": "A - Via Aérea",
                "checks": ["Posição da traqueia", "Nível da carina", "Corpos estranhos", "Estreitamento traqueal"],
                "observation": "A traqueia está na linha média sem desvio. Carina aproximadamente no nível T4-T5 (normal). Nenhum corpo estranho ou estreitamento traqueal visível.",
            },
            {
                "step": "B - Ossos",
                "checks": ["Simetria das clavículas", "Fraturas de costelas", "Alinhamento da coluna", "Lesões líticas/blásticas"],
                "observation": "Clavículas são simétricas e intactas, confirmando bom posicionamento. Sem fraturas de costelas. Alinhamento da coluna torácica normal. Sem lesões líticas ou blásticas.",
            },
            {
                "step": "C - Cardíaco",
                "checks": ["Medição do ICT", "Bordas do coração", "Pericárdio", "Grandes vasos"],
                "observation": "ICT aproximadamente 0,48-0,50 (limítrofe normal). Borda cardíaca direita bem definida (átrio direito). Borda cardíaca esquerda mostra leve proeminência (ventrículo esquerdo). Sem calcificação pericárdica.",
            },
            {
                "step": "D - Diafragma",
                "checks": ["Posição dos hemidiafragmas", "Ângulos costofrênicos", "Ar livre", "Bolha gástrica"],
                "observation": "Hemidiafragma direito discretamente mais elevado que o esquerdo (normal). Ambos os ângulos costofrênicos agudos, descartando derrame pleural. Sem ar subdiafragmático livre. Bolha gástrica visível sob o hemidiafragma esquerdo.",
            },
            {
                "step": "E - Todo o Resto",
                "checks": ["Campos pulmonares", "Hilos", "Pleura", "Tecidos moles", "Linhas/tubos"],
                "observation": "Campos pulmonares claros bilateralmente. Estruturas hilares normais em tamanho e posição. Sem espessamento pleural ou derrame. Tecidos moles sem alterações. Sem tubos, linhas ou dispositivos presentes.",
            },
        ],
        "pathology_scenarios": [
            {
                "condition": "Pneumonia",
                "icon": "\U0001F9EB",
                "current_status": "Campos pulmonares aparecem claros sem consolidação ou infiltrados.",
                "what_would_change": "Pneumonia lobar: opacidade branca densa preenchendo um lobo inteiro com broncogramas aéreos. Broncopneumonia: opacidades irregulares mal definidas espalhadas pelos pulmões, frequentemente bilateral.",
                "key_signs": [
                    "Consolidação (opacidade branca densa)",
                    "Broncogramas aéreos (tubos ramificados escuros dentro da opacidade)",
                    "Sinal da silhueta (perda de borda nítida com coração/diafragma)",
                    "Derrame pleural parapneumônico (embotamento costofrênico)",
                ],
                "teaching_point": "Lobos médio e inferior direitos são mais comumente afetados na pneumonia aspirativa. Pneumonia do lobo inferior esquerdo se esconde atrás do coração - sempre verifique o espaço retrocardíaco.",
            },
            {
                "condition": "Insuficiência Cardíaca / Cardiomegalia",
                "icon": "\u2764\uFE0F",
                "current_status": "Silhueta cardíaca é limítrofe com ICT ~0,48-0,50. Sem sinais de edema pulmonar.",
                "what_would_change": "ICT excede 0,5, cefalização de veias do lobo superior, linhas B de Kerley na periferia, manguito peribrônquico, e em casos graves padrão de asa de morcego/borboleta de edema pulmonar bilateral.",
                "key_signs": [
                    "ICT > 0,5 (cardiomegalia)",
                    "Cefalização dos vasos do lobo superior",
                    "Linhas B de Kerley (linhas horizontais curtas na periferia pulmonar)",
                    "Padrão de asa de morcego (edema alveolar bilateral)",
                    "Derrames pleurais bilaterais (frequentemente maior à direita)",
                ],
                "teaching_point": "Insuficiência cardíaca progride de cefalização (leve) para edema intersticial com linhas B de Kerley (moderado) para edema alveolar com padrão de asa de morcego (grave). O tamanho cardíaco limítrofe aqui justifica acompanhamento.",
            },
            {
                "condition": "Derrame Pleural",
                "icon": "\U0001F4A7",
                "current_status": "Ambos os ângulos costofrênicos estão agudos, descartando derrame significativo.",
                "what_would_change": "Derrame pequeno: embotamento sutil do ângulo costofrênico. Moderado: sinal do menisco com borda superior côncava. Grande: opacificação do hemitórax inferior com desvio mediastinal para o lado oposto.",
                "key_signs": [
                    "Embotamento do ângulo costofrênico (sinal mais precoce, ~200-300ml)",
                    "Sinal do menisco (borda côncava do fluido)",
                    "Desvio mediastinal para longe do derrame grande",
                    "Opacificação completa do hemitórax (derrame maciço)",
                ],
                "teaching_point": "Derrame empurra estruturas PARA LONGE do lado afetado, enquanto atelectasia puxa estruturas EM DIREÇÃO a ele. Esta distinção chave ajuda a diferenciar os dois no raio-X.",
            },
            {
                "condition": "Pneumotórax",
                "icon": "\U0001F4A8",
                "current_status": "Marcas pulmonares se estendem até a periferia da parede torácica bilateralmente - sem pneumotórax.",
                "what_would_change": "Uma linha pleural visceral fina separaria o pulmão aerado do espaço aéreo pleural, sem marcas pulmonares além desta linha. Pneumotórax hipertensivo causa desvio mediastinal para o lado oposto.",
                "key_signs": [
                    "Linha pleural visceral (linha branca fina na borda do pulmão)",
                    "Marcas pulmonares ausentes além da linha pleural",
                    "Sinal do sulco profundo (em filmes em decúbito dorsal)",
                    "Desvio mediastinal (pneumotórax hipertensivo - EMERGÊNCIA)",
                ],
                "teaching_point": "Pneumotórax hipertensivo é uma emergência clínica. Procure por desvio mediastinal para o lado oposto, hemidiafragma achatado e colapso cardiovascular. Requer descompressão imediata com agulha.",
            },
        ],
        "clinical_pearls": [
            {
                "category": "Achados Normais",
                "icon": "\u2705",
                "items": [
                    {"title": "Ângulos costofrênicos agudos", "detail": "Descarta derrame pleural significativo (~200-300ml necessários para embotar em filme vertical)."},
                    {"title": "Traqueia na linha média", "detail": "Argumenta contra pneumotórax hipertensivo, derrame grande ou massa mediastinal."},
                    {"title": "Clavículas simétricas", "detail": "Confirma posicionamento adequado do paciente sem artefato de rotação."},
                ],
            },
            {
                "category": "Medidas Importantes",
                "icon": "\U0001F4CF",
                "items": [
                    {"title": "ICT (Índice Cardiotorácico)", "detail": "Largura cardíaca máxima / largura torácica máxima. Normal < 0,5 em filme PA. Esta imagem: ~0,48-0,50."},
                    {"title": "Largura mediastinal", "detail": "Deve ser < 8cm em PA. Maior levanta preocupação para patologia aórtica."},
                    {"title": "Posição traqueal", "detail": "Linha média ou levemente à direita no nível do arco aórtico é normal."},
                ],
            },
            {
                "category": "Armadilhas Comuns",
                "icon": "\u26A0\uFE0F",
                "items": [
                    {"title": "Filmes AP vs PA", "detail": "AP aumenta o coração em ~20%. Sempre confirme PA antes de diagnosticar cardiomegalia."},
                    {"title": "Artefato de rotação", "detail": "Faz um pulmão parecer mais branco, imitando patologia. Verifique simetria das clavículas para detectar."},
                    {"title": "Subpenetração", "detail": "Faz os pulmões parecerem mais brancos. Você deve ver corpos vertebrais levemente através do coração em um filme adequadamente penetrado."},
                    {"title": "Espaço retrocardíaco", "detail": "Pneumonia do lobo inferior esquerdo e hérnias de hiato se escondem aqui - sempre olhe cuidadosamente."},
                ],
            },
            {
                "category": "Próximos Passos",
                "icon": "\U0001F9ED",
                "items": [
                    {"title": "Comparar com imagens prévias", "detail": "Avaliar mudança intervalar, especialmente dado o tamanho cardíaco limítrofe."},
                    {"title": "Correlação clínica", "detail": "Correlacionar com sintomas e achados do exame físico."},
                    {"title": "Vista lateral", "detail": "Considerar para avaliação retrocardíaca/retroesternal."},
                ],
            },
        ],
        "disclaimer": "Esta análise é apenas para fins educacionais e não deve ser considerada um substituto para aconselhamento médico profissional. Sempre consulte um profissional de saúde qualificado para tomada de decisões clínicas.",
    }
