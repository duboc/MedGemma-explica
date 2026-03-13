"""Gemini Flash integration for educational explanations and Q&A chat."""

import logging

from config import settings

logger = logging.getLogger(__name__)


def _get_gemini_url() -> str:
    loc = settings.gemini_location
    if loc == "global":
        host = "aiplatform.googleapis.com"
    else:
        host = f"{loc}-aiplatform.googleapis.com"
    return (
        f"https://{host}/v1/projects/"
        f"{settings.project_id}/locations/{loc}/publishers/google/"
        f"models/{settings.gemini_model}:generateContent"
    )


def _get_access_token() -> str:
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token


def _call_gemini(
    contents: list[dict],
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    max_output_tokens: int = 2048,
) -> str:
    """Call Gemini Flash via Vertex AI REST API."""
    import requests

    access_token = _get_access_token()

    generation_config: dict = {
        "temperature": 0.7,
        "maxOutputTokens": max_output_tokens,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    payload: dict = {
        "contents": contents,
        "generationConfig": generation_config,
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    resp = requests.post(
        _get_gemini_url(),
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    resp.raise_for_status()

    result = resp.json()
    candidates = result.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return ""


SYSTEM_INSTRUCTION = """You are an expert medical educator specializing in radiology and anatomy.
You help medical students and healthcare learners understand chest X-ray findings.
Your explanations are accurate, educational, and engaging.
Use clear language appropriate for the specified level.
Always include a disclaimer that this is for educational purposes only, not clinical diagnosis."""


def explain_analysis(
    structure_names: list[str],
    bounding_boxes: list[dict],
    educational_infos: list[dict],
    level: str = "medical_student",
) -> str:
    """Generate a rich educational explanation using Gemini Flash."""
    level_descriptions = {
        "pre_med": "a pre-medical student with basic anatomy knowledge",
        "medical_student": "a medical student studying radiology",
        "resident": "a radiology resident in training",
        "attending": "a practicing physician refreshing their knowledge",
    }
    audience = level_descriptions.get(level, level_descriptions["medical_student"])

    structures_context = []
    for i, name in enumerate(structure_names):
        info = educational_infos[i] if i < len(educational_infos) else {}
        boxes = [b for b in bounding_boxes if b.get("label", "").lower() == name.lower()]
        structures_context.append(
            f"- **{name}**: {info.get('description', 'N/A')} "
            f"(Clinical: {info.get('clinical_relevance', 'N/A')}). "
            f"Detected {len(boxes)} bounding box(es)."
        )

    prompt = f"""A chest X-ray analysis was performed using MedGemma, which identified the following anatomical structures:

{chr(10).join(structures_context)}

Please provide a comprehensive educational explanation for {audience}. Include:

1. **What You're Seeing**: Explain what these structures look like on a chest X-ray and how to identify them.
2. **Normal vs. Abnormal**: Describe what normal appearance looks like and key signs that might indicate pathology.
3. **Clinical Connections**: How do these structures relate to common clinical conditions?
4. **Study Tips**: Key points to remember for identifying these structures on X-rays.

Format your response in clear sections with markdown."""

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    return _call_gemini(contents, system_instruction=SYSTEM_INSTRUCTION)


def chat_about_analysis(
    messages: list[dict],
    structure_names: list[str],
    educational_infos: list[dict],
) -> str:
    """Handle a multi-turn Q&A conversation about the analysis."""
    context = []
    for i, name in enumerate(structure_names):
        info = educational_infos[i] if i < len(educational_infos) else {}
        context.append(f"- {name}: {info.get('description', '')} Clinical: {info.get('clinical_relevance', '')}")

    system = f"""{SYSTEM_INSTRUCTION}

The current analysis involves these chest X-ray structures:
{chr(10).join(context)}

Answer questions about these structures, the X-ray findings, related pathology, or radiology concepts.
Keep answers focused and educational. Use markdown formatting."""

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    return _call_gemini(contents, system_instruction=system)


def mock_explain(structure_names: list[str], level: str = "medical_student") -> str:
    """Return a mock educational explanation for testing."""
    names = ", ".join(structure_names)
    return f"""## Educational Overview: {names}

### What You're Seeing
On this chest X-ray, MedGemma has identified and localized the **{names}**. These structures are fundamental landmarks in chest radiograph interpretation.

### Normal vs. Abnormal
In a normal chest X-ray, these structures should appear symmetric (where applicable) and within expected size ranges. Key things to look for:
- **Size**: Is the structure within normal proportions?
- **Shape**: Are the contours smooth and regular?
- **Position**: Is everything in the expected anatomical location?
- **Density**: Is the radiodensity what you'd expect?

### Clinical Connections
Understanding these structures is essential for identifying conditions such as pneumonia, pleural effusions, cardiomegaly, and pneumothorax.

### Study Tips
- Always use a systematic approach when reading chest X-rays
- Compare left and right sides for symmetry
- Follow the ABCDEs: Airway, Bones, Cardiac, Diaphragm, Everything else

> *This explanation is for educational purposes only, not for clinical diagnosis.*"""


def mock_chat(message: str, structure_names: list[str]) -> str:
    """Return a mock chat response for testing."""
    names = ", ".join(structure_names)
    return f"""Great question! In the context of the **{names}** visible on this chest X-ray:

{message.strip()} is an important topic in radiology education. Here are the key points:

1. **Anatomical Context**: The structures identified by MedGemma serve as important landmarks for systematic chest X-ray interpretation.

2. **Clinical Significance**: Understanding the normal appearance helps recognize pathological changes early.

3. **Practice Tip**: Try comparing multiple X-rays to build pattern recognition skills.

> *This is for educational purposes only, not for clinical diagnosis.*"""
