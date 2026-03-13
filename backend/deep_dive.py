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
- Be specific to what is described in the input about THIS image"""


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
            "This explanation is for educational purposes only and should not be "
            "used for clinical diagnosis. Always consult a qualified healthcare provider."
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
                    "title": "Analysis",
                    "icon": "clipboard",
                    "content": raw_text[:2000],
                    "key_points": [],
                }
            ],
            "disclaimer": "This explanation is for educational purposes only.",
        }


def mock_deep_dive(structure_names: list[str], level: str = "medical_student") -> dict:
    """Return a realistic mock deep dive for UI testing."""
    names = ", ".join(structure_names)
    first = structure_names[0] if structure_names else "chest structures"

    return {
        "title": f"Educational Deep Dive: {names}",
        "level": level,
        "sections": [
            {
                "id": "identification",
                "title": "What You're Seeing",
                "icon": "eye",
                "content": f"On this chest X-ray, MedGemma has identified and localized the {names}. These structures are fundamental landmarks in chest radiograph interpretation that every medical professional should be able to identify confidently.",
                "key_points": [
                    {
                        "term": first.title(),
                        "detail": f"The {first} is clearly visible in its expected anatomical position. On a well-positioned PA film, it should appear symmetric with its contralateral counterpart (where applicable).",
                    },
                    {
                        "term": "Radiographic Density",
                        "detail": "Different tissues absorb X-rays differently: air (black), fat (dark grey), soft tissue/fluid (light grey), bone/calcium (white), metal (bright white).",
                    },
                    {
                        "term": "Anatomical Landmarks",
                        "detail": "Use surrounding structures as reference points. The carina, aortic arch, and hemidiaphragms are reliable landmarks for orientation.",
                    },
                    {
                        "term": "Image Quality",
                        "detail": "Before interpreting, check: PA vs AP, rotation (clavicle symmetry), penetration (vertebrae visible through heart), inspiration (6+ anterior ribs).",
                    },
                ],
            },
            {
                "id": "normal_vs_abnormal",
                "title": "Normal vs. Abnormal",
                "icon": "balance",
                "comparisons": [
                    {
                        "structure": first.title(),
                        "normal": f"The {first} appears in its expected position with normal size, shape, and density. Borders are well-defined.",
                        "abnormal_signs": [
                            "Increased or decreased density",
                            "Shift from normal position",
                            "Loss of normal borders (silhouette sign)",
                            "Unexpected size change",
                        ],
                        "this_image": f"The {first} appears within normal limits on this image with no signs of acute pathology.",
                    },
                    {
                        "structure": "Overall Assessment",
                        "normal": "Symmetric lung fields, normal cardiac silhouette (CTR < 0.5), sharp costophrenic angles, midline trachea.",
                        "abnormal_signs": [
                            "Asymmetric lung opacity",
                            "Widened mediastinum",
                            "Blunted costophrenic angles",
                            "Tracheal deviation",
                        ],
                        "this_image": "The overall chest appearance is unremarkable with no acute findings.",
                    },
                ],
            },
            {
                "id": "clinical_connections",
                "title": "Clinical Connections",
                "icon": "stethoscope",
                "connections": [
                    {
                        "condition": "Pneumonia",
                        "relevance": f"Infection can cause consolidation adjacent to or within the {first}, appearing as increased opacity with possible air bronchograms.",
                        "what_to_look_for": "Focal consolidation, air bronchograms, silhouette sign, parapneumonic effusion",
                    },
                    {
                        "condition": "Heart Failure",
                        "relevance": "Fluid overload manifests as cardiomegaly, cephalization of vessels, Kerley B lines, and bilateral effusions.",
                        "what_to_look_for": "CTR > 0.5, upper lobe vessel distension, perihilar haziness, bilateral pleural effusions",
                    },
                    {
                        "condition": "Pneumothorax",
                        "relevance": "Air in the pleural space causes lung collapse. The visceral pleural line becomes visible with absent lung markings peripherally.",
                        "what_to_look_for": "Visceral pleural line, absent peripheral lung markings, deep sulcus sign (supine), mediastinal shift (tension)",
                    },
                ],
            },
            {
                "id": "study_tips",
                "title": "Study Tips",
                "icon": "lightbulb",
                "tips": [
                    {
                        "tip": "Use the ABCDE systematic approach",
                        "why": "Airway, Bones, Cardiac, Diaphragm, Everything else - ensures you never miss a finding by being methodical.",
                    },
                    {
                        "tip": "Always compare with the contralateral side",
                        "why": "Asymmetry is often the first clue to pathology. Train your eye to spot subtle differences between left and right.",
                    },
                    {
                        "tip": "Check the edges and corners",
                        "why": "Apices, costophrenic angles, and retrocardiac space are common 'blind spots' where findings are missed.",
                    },
                    {
                        "tip": "Know your lines and tubes",
                        "why": "In clinical practice, confirming correct placement of ET tubes, central lines, and chest drains is a critical skill.",
                    },
                ],
            },
        ],
        "disclaimer": "This explanation is for educational purposes only and should not be used for clinical diagnosis. Always consult a qualified healthcare provider.",
    }
