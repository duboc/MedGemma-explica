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

Be thorough and specific to THIS image."""

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
- Keep text concise but informative"""


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
            "This analysis is for educational purposes only and should not be considered "
            "a substitute for professional medical advice. Always consult a qualified "
            "healthcare provider for clinical decision-making."
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
        "disclaimer": "This analysis is for educational purposes only. Gemini structuring was unavailable; showing extracted findings.",
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
- status should reflect what was observed on THIS image"""


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
            {"name": n, "appearance": "Analysis available", "status": "normal", "notable": "", "clinical_note": ""}
            for n in structure_names
        ]


def mock_structure_findings(structure_names: list[str]) -> list[dict]:
    """Return mock per-structure findings for UI testing."""
    mock_data = {
        "right lung": {
            "appearance": "Clear lung field with normal bronchovascular markings extending to the periphery",
            "status": "normal",
            "notable": "No focal consolidation, mass, or pleural effusion. Sharp right costophrenic angle.",
            "clinical_note": "The right main bronchus is wider and more vertical, making it the most common site for aspirated foreign bodies.",
        },
        "left lung": {
            "appearance": "Clear lung field, partially obscured by the cardiac silhouette in the retrocardiac region",
            "status": "normal",
            "notable": "No consolidation or effusion. The lingula and left lower lobe appear clear.",
            "clinical_note": "Always check the retrocardiac space carefully - left lower lobe pneumonia can hide behind the heart.",
        },
        "heart": {
            "appearance": "Cardiac silhouette with well-defined borders, CTR approximately 0.48-0.50",
            "status": "borderline",
            "notable": "Borderline cardiac size at the upper limit of normal. Left heart border slightly prominent.",
            "clinical_note": "CTR > 0.5 on a PA film suggests cardiomegaly. AP films magnify the heart by ~20%, so always confirm PA positioning.",
        },
        "trachea": {
            "appearance": "Air-filled tubular structure in the midline of the upper mediastinum",
            "status": "normal",
            "notable": "Midline position with no deviation. Carina at approximately T4-T5 level.",
            "clinical_note": "Tracheal deviation can indicate tension pneumothorax (away from affected side) or atelectasis (toward affected side).",
        },
        "aortic arch": {
            "appearance": "Rounded opacity visible on the left side of the mediastinum above the left hilum",
            "status": "normal",
            "notable": "Normal caliber with no unfolding or calcification visible.",
            "clinical_note": "A widened mediastinum (>8cm) may suggest aortic dissection or aneurysm - measure carefully.",
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
                "appearance": f"The {name} is visible in its expected anatomical position",
                "status": "normal",
                "notable": "No acute abnormality identified.",
                "clinical_note": f"The {name} is an important landmark in systematic chest X-ray interpretation.",
            })
    return results


def mock_findings_report(structure_names: list[str]) -> dict:
    """Return a realistic mock findings report for UI testing."""
    names = ", ".join(structure_names) if structure_names else "chest structures"
    return {
        "overall_assessment": {
            "summary": f"PA chest radiograph demonstrates generally normal cardiopulmonary anatomy with focus on {names}. No acute cardiopulmonary process identified.",
            "findings": [
                {
                    "structure": "Heart",
                    "status": "borderline",
                    "finding": "Borderline cardiac silhouette size",
                    "detail": "Cardiothoracic ratio (CTR) approximately 0.48-0.50, at the upper limit of normal. Left heart border slightly prominent.",
                },
                {
                    "structure": "Right Lung",
                    "status": "normal",
                    "finding": "Clear lung field",
                    "detail": "Well-aerated with no focal consolidation, mass, or pleural effusion. Normal bronchovascular markings throughout.",
                },
                {
                    "structure": "Left Lung",
                    "status": "normal",
                    "finding": "Clear lung field",
                    "detail": "Left lung field appears clear. Cardiac silhouette partially obscures the retrocardiac region, but no obvious abnormality identified.",
                },
                {
                    "structure": "Mediastinum",
                    "status": "normal",
                    "finding": "Midline, not widened",
                    "detail": "The mediastinum is midline and not widened. Aortic arch is within normal limits.",
                },
                {
                    "structure": "Diaphragm",
                    "status": "normal",
                    "finding": "Smooth, well-defined hemidiaphragms",
                    "detail": "Right hemidiaphragm slightly higher than left (normal). Costophrenic angles sharp bilaterally.",
                },
                {
                    "structure": "Bones",
                    "status": "normal",
                    "finding": "No fractures or lesions",
                    "detail": "Visible clavicles, ribs, and thoracic spine show no fractures or lytic lesions. Symmetric clavicles confirm good positioning.",
                },
            ],
        },
        "systematic_approach": [
            {
                "step": "A - Airway",
                "checks": ["Trachea position", "Carina level", "Foreign bodies", "Tracheal narrowing"],
                "observation": "Trachea is midline with no deviation. Carina at approximately T4-T5 level (normal). No foreign body or tracheal narrowing visible.",
            },
            {
                "step": "B - Bones",
                "checks": ["Clavicle symmetry", "Rib fractures", "Spine alignment", "Lytic/blastic lesions"],
                "observation": "Clavicles are symmetric and intact, confirming good positioning. No rib fractures. Thoracic spine alignment normal. No lytic or blastic lesions.",
            },
            {
                "step": "C - Cardiac",
                "checks": ["CTR measurement", "Heart borders", "Pericardium", "Great vessels"],
                "observation": "CTR approximately 0.48-0.50 (borderline normal). Right heart border well-defined (right atrium). Left heart border shows slight prominence (left ventricle). No pericardial calcification.",
            },
            {
                "step": "D - Diaphragm",
                "checks": ["Hemidiaphragm position", "Costophrenic angles", "Free air", "Gastric bubble"],
                "observation": "Right hemidiaphragm slightly higher than left (normal). Both costophrenic angles sharp, ruling out pleural effusion. No subdiaphragmatic free air. Gastric bubble visible under left hemidiaphragm.",
            },
            {
                "step": "E - Everything Else",
                "checks": ["Lung fields", "Hila", "Pleura", "Soft tissues", "Lines/tubes"],
                "observation": "Lung fields clear bilaterally. Hilar structures normal in size and position. No pleural thickening or effusion. Soft tissues unremarkable. No tubes, lines, or devices present.",
            },
        ],
        "pathology_scenarios": [
            {
                "condition": "Pneumonia",
                "icon": "\U0001F9EB",
                "current_status": "Lung fields appear clear with no consolidation or infiltrates.",
                "what_would_change": "Lobar pneumonia: dense white opacity filling an entire lobe with air bronchograms. Bronchopneumonia: patchy, poorly defined opacities scattered through the lungs, often bilateral.",
                "key_signs": [
                    "Consolidation (dense white opacity)",
                    "Air bronchograms (dark branching tubes within opacity)",
                    "Silhouette sign (loss of sharp border with heart/diaphragm)",
                    "Parapneumonic pleural effusion (costophrenic blunting)",
                ],
                "teaching_point": "Right middle and lower lobes are most commonly affected in aspiration pneumonia. Left lower lobe pneumonia hides behind the heart - always check the retrocardiac space.",
            },
            {
                "condition": "Heart Failure / Cardiomegaly",
                "icon": "\u2764\uFE0F",
                "current_status": "Cardiac silhouette is borderline with CTR ~0.48-0.50. No signs of pulmonary edema.",
                "what_would_change": "CTR exceeds 0.5, upper lobe vein cephalization, Kerley B lines at periphery, peribronchial cuffing, and in severe cases bat-wing/butterfly pattern of bilateral pulmonary edema.",
                "key_signs": [
                    "CTR > 0.5 (cardiomegaly)",
                    "Cephalization of upper lobe vessels",
                    "Kerley B lines (short horizontal lines at lung periphery)",
                    "Bat-wing pattern (bilateral alveolar edema)",
                    "Bilateral pleural effusions (often larger on right)",
                ],
                "teaching_point": "Heart failure progresses from cephalization (mild) to interstitial edema with Kerley B lines (moderate) to alveolar edema with bat-wing pattern (severe). The borderline heart size here warrants follow-up.",
            },
            {
                "condition": "Pleural Effusion",
                "icon": "\U0001F4A7",
                "current_status": "Both costophrenic angles are sharp, ruling out significant effusion.",
                "what_would_change": "Small effusion: subtle blunting of costophrenic angle. Moderate: meniscus sign with concave upper border. Large: opacification of lower hemithorax with mediastinal shift away.",
                "key_signs": [
                    "Costophrenic angle blunting (earliest sign, ~200-300ml)",
                    "Meniscus sign (concave fluid border)",
                    "Mediastinal shift away from large effusion",
                    "Complete hemithorax whiteout (massive effusion)",
                ],
                "teaching_point": "Effusion pushes structures AWAY from the affected side, while atelectasis pulls structures TOWARD it. This key distinction helps differentiate the two on X-ray.",
            },
            {
                "condition": "Pneumothorax",
                "icon": "\U0001F4A8",
                "current_status": "Lung markings extend to the chest wall periphery bilaterally - no pneumothorax.",
                "what_would_change": "A thin visceral pleural line would separate aerated lung from the pleural air space, with no lung markings beyond this line. Tension pneumothorax causes mediastinal shift to opposite side.",
                "key_signs": [
                    "Visceral pleural line (thin white line at lung edge)",
                    "Absent lung markings beyond pleural line",
                    "Deep sulcus sign (on supine films)",
                    "Mediastinal shift (tension pneumothorax - EMERGENCY)",
                ],
                "teaching_point": "Tension pneumothorax is a clinical emergency. Look for mediastinal shift to the opposite side, flattened hemidiaphragm, and cardiovascular collapse. Requires immediate needle decompression.",
            },
        ],
        "clinical_pearls": [
            {
                "category": "Normal Findings",
                "icon": "\u2705",
                "items": [
                    {"title": "Sharp costophrenic angles", "detail": "Rules out significant pleural effusion (~200-300ml needed to blunt on upright film)."},
                    {"title": "Midline trachea", "detail": "Argues against tension pneumothorax, large effusion, or mediastinal mass."},
                    {"title": "Symmetric clavicles", "detail": "Confirms proper patient positioning with no rotation artifact."},
                ],
            },
            {
                "category": "Key Measurements",
                "icon": "\U0001F4CF",
                "items": [
                    {"title": "CTR (Cardiothoracic Ratio)", "detail": "Max cardiac width / max thoracic width. Normal < 0.5 on PA film. This image: ~0.48-0.50."},
                    {"title": "Mediastinal width", "detail": "Should be < 8cm on PA. Wider raises concern for aortic pathology."},
                    {"title": "Tracheal position", "detail": "Midline or slightly right at the aortic arch level is normal."},
                ],
            },
            {
                "category": "Common Pitfalls",
                "icon": "\u26A0\uFE0F",
                "items": [
                    {"title": "AP vs PA films", "detail": "AP magnifies the heart by ~20%. Always confirm PA before diagnosing cardiomegaly."},
                    {"title": "Rotation artifact", "detail": "Makes one lung appear whiter, mimicking pathology. Check clavicle symmetry to detect."},
                    {"title": "Underpenetration", "detail": "Makes lungs look whiter. You should see vertebral bodies faintly through the heart on a properly penetrated film."},
                    {"title": "Retrocardiac space", "detail": "Left lower lobe pneumonia and hiatal hernias hide here - always look carefully."},
                ],
            },
            {
                "category": "Next Steps",
                "icon": "\U0001F9ED",
                "items": [
                    {"title": "Compare with prior imaging", "detail": "Assess for interval change, especially given borderline cardiac size."},
                    {"title": "Clinical correlation", "detail": "Correlate with symptoms and physical exam findings."},
                    {"title": "Lateral view", "detail": "Consider for retrocardiac/retrosternal evaluation."},
                ],
            },
        ],
        "disclaimer": "This analysis is for educational purposes only and should not be considered a substitute for professional medical advice. Always consult a qualified healthcare provider for clinical decision-making.",
    }
