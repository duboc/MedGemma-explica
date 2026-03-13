import json
import re

from config import settings


ANATOMY_INFO = {
    "right lung": {
        "description": "O pulmão direito possui três lobos (superior, médio e inferior) e é ligeiramente maior que o pulmão esquerdo.",
        "clinical_relevance": "Local comum para pneumonia, nódulos pulmonares e derrames pleurais. O brônquio principal direito é mais largo e vertical, sendo o local mais comum para aspiração de corpos estranhos.",
    },
    "left lung": {
        "description": "O pulmão esquerdo possui dois lobos (superior e inferior) e é ligeiramente menor para acomodar o coração.",
        "clinical_relevance": "A língula do lobo superior esquerdo é o equivalente anatômico do lobo médio direito. A incisura cardíaca cria uma indentação característica.",
    },
    "heart": {
        "description": "A silhueta cardíaca em uma radiografia PA de tórax normalmente ocupa menos de 50% da largura torácica (índice cardiotorácico).",
        "clinical_relevance": "Uma silhueta cardíaca aumentada (ICT > 0,5) pode indicar cardiomegalia, derrame pericárdico ou outras condições cardíacas.",
    },
    "right clavicle": {
        "description": "A clavícula conecta o esterno à escápula. Na radiografia, aparece como um osso curvo e denso no topo do tórax.",
        "clinical_relevance": "Fraturas são comuns, especialmente no terço médio. A clavícula é um marco importante para identificar os ápices pulmonares.",
    },
    "left clavicle": {
        "description": "A clavícula esquerda espelha a direita, conectando o esterno à escápula esquerda.",
        "clinical_relevance": "A simetria entre as clavículas ajuda a avaliar a rotação do paciente na radiografia. Assimetria pode indicar posicionamento inadequado ou patologia.",
    },
    "trachea": {
        "description": "A traqueia aparece como um tubo escuro preenchido por ar na linha média do tórax superior, bifurcando-se na carina nos brônquios principais esquerdo e direito.",
        "clinical_relevance": "O desvio traqueal pode indicar pneumotórax hipertensivo, derrame pleural volumoso ou massa mediastinal. A carina está tipicamente no nível de T4-T5.",
    },
    "aortic arch": {
        "description": "O arco aórtico (botão aórtico) aparece como uma opacidade arredondada no lado esquerdo do mediastino, logo acima do hilo esquerdo.",
        "clinical_relevance": "Uma aorta desdobrada ou alargada pode sugerir aneurisma, aterosclerose ou lesão traumática. O botão aórtico é um marco importante.",
    },
    "right costophrenic angle": {
        "description": "O ângulo costofrênico é onde o diafragma encontra a parede torácica. Normalmente aparece como um ângulo agudo e nítido.",
        "clinical_relevance": "O velamento do ângulo costofrênico é um dos sinais mais precoces de derrame pleural, detectável quando aproximadamente 200-300mL de líquido estão presentes.",
    },
    "left costophrenic angle": {
        "description": "O ângulo costofrênico esquerdo espelha o lado direito na junção do hemidiafragma esquerdo com a parede torácica lateral.",
        "clinical_relevance": "Derrame pleural à esquerda pode estar associado a insuficiência cardíaca, derrame parapneumônico ou outras condições.",
    },
    "upper mediastinum": {
        "description": "O mediastino superior contém os grandes vasos, traqueia, esôfago e ducto torácico, visíveis acima do nível do pericárdio.",
        "clinical_relevance": "O alargamento do mediastino superior pode sugerir dissecção aórtica, linfonodomegalia ou lesões expansivas.",
    },
    "right hilar structures": {
        "description": "O hilo direito contém a artéria pulmonar direita, o brônquio principal direito e linfonodos associados.",
        "clinical_relevance": "O aumento hilar pode indicar linfonodomegalia (sarcoidose, linfoma, infecção) ou hipertensão arterial pulmonar.",
    },
    "left hilar structures": {
        "description": "O hilo esquerdo é normalmente ligeiramente mais alto que o direito e contém a artéria pulmonar esquerda e o brônquio principal esquerdo.",
        "clinical_relevance": "O hilo esquerdo é normalmente 1-2 cm mais alto que o direito. Uma mudança nessa relação pode indicar perda de volume ou efeito de massa.",
    },
    "spine": {
        "description": "A coluna torácica é visível através da silhueta cardíaca em uma incidência PA bem penetrada, com os corpos vertebrais tornando-se mais transparentes inferiormente.",
        "clinical_relevance": "A perda da transparência progressiva normal inferiormente pode sugerir patologia do mediastino posterior ou consolidação retrocardíaca.",
    },
    "right hemidiaphragm": {
        "description": "O hemidiafragma direito é normalmente ligeiramente mais alto que o esquerdo (1-2 cm) devido ao fígado subjacente.",
        "clinical_relevance": "O achatamento do diafragma sugere hiperinsuflação (DPOC/enfisema). A elevação pode indicar paralisia do nervo frênico ou derrame subpulmonar.",
    },
    "left hemidiaphragm": {
        "description": "O hemidiafragma esquerdo é normalmente ligeiramente mais baixo que o direito. A bolha gástrica é tipicamente vista abaixo dele.",
        "clinical_relevance": "O sinal da bolha gástrica abaixo do hemidiafragma esquerdo é um marco útil. A perda desse sinal pode indicar patologia do lobo inferior esquerdo.",
    },
}


def build_prompt(object_name: str) -> str:
    """Build the localization prompt for MedGemma."""
    return f"""Instructions:
The following user query will require outputting bounding boxes. The format of bounding boxes coordinates is [y0, x0, y1, x1] where (y0, x0) must be top-left corner and (y1, x1) the bottom-right corner. This implies that x0 < x1 and y0 < y1. Always normalize the x and y coordinates the range [0, 1000], meaning that a bounding box starting at 15% of the image width would be associated with an x coordinate of 150. You MUST output a single parseable json list of objects enclosed into ```json...``` brackets, for instance ```json[{{"box_2d": [800, 3, 840, 471], "label": "car"}}, {{"box_2d": [400, 22, 600, 73], "label": "dog"}}]``` is a valid output. Now answer to the user query.

Remember "left" refers to the patient's left side where the heart is and sometimes underneath an L in the upper right corner of the image.

Query:
Where is the {object_name}? Don't give a final answer without reasoning. Output the final answer in the format "Final Answer: X" where X is a JSON list of objects. The object needs a "box_2d" and "label" key. Answer:"""


def parse_bounding_boxes(response: str) -> list[dict]:
    """Extract bounding box data from model response. Prefers the last json block (Final Answer)."""
    # Find all ```json...``` blocks and use the last one (usually the Final Answer)
    matches = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    for match in reversed(matches):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return []


def _call_medgemma(messages: list[dict], max_tokens: int = 1000) -> str:
    """Send messages to MedGemma endpoint and return raw response text."""
    import google.auth
    import google.auth.transport.requests
    import requests

    credentials, _ = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    access_token = credentials.token

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
            "Authorization": f"Bearer {access_token}",
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


def predict_with_medgemma(image_bytes: bytes, object_name: str) -> tuple[str, list[dict]]:
    """Call MedGemma via Vertex AI endpoint for bounding box localization."""
    import base64

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = build_prompt(object_name)

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are an expert radiologist."}],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        },
    ]

    response_text = _call_medgemma(messages)

    # Remove thinking traces if present
    if "<end_of_turn>" in response_text:
        response_text = response_text.split("<end_of_turn>", 1)[0]

    bounding_boxes = parse_bounding_boxes(response_text)

    for prefix in ["<thought>", "thought"]:
        if response_text.startswith(prefix):
            fa_idx = response_text.find("Final Answer:")
            if fa_idx != -1:
                response_text = response_text[fa_idx:]
            break

    return response_text, bounding_boxes


def explain_with_medgemma(
    image_bytes: bytes | None,
    structure_names: list[str],
    educational_infos: list[dict],
    level: str = "medical_student",
) -> str:
    """Generate educational explanation using MedGemma, optionally with the X-ray image."""
    import base64

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
        structures_context.append(
            f"- {name}: {info.get('description', 'N/A')} "
            f"(Clinical: {info.get('clinical_relevance', 'N/A')})"
        )

    prompt = f"""You have analyzed this chest X-ray and identified the following anatomical structures:

{chr(10).join(structures_context)}

Please provide a comprehensive educational explanation for {audience}. Include:

1. **What You're Seeing**: Explain what these structures look like on this chest X-ray and how to identify them.
2. **Normal vs. Abnormal**: Describe what normal appearance looks like and key signs that might indicate pathology.
3. **Clinical Connections**: How do these structures relate to common clinical conditions?
4. **Study Tips**: Key points to remember for identifying these structures on X-rays.

Format your response in clear sections with markdown. Include a disclaimer that this is for educational purposes only.

IMPORTANT: Write your entire response in Brazilian Portuguese (pt-BR)."""

    user_content: list[dict] = [{"type": "text", "text": prompt}]
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are an expert medical educator specializing in radiology and anatomy. You help learners understand chest X-ray findings with accurate, engaging explanations."}],
        },
        {"role": "user", "content": user_content},
    ]

    response_text = _call_medgemma(messages, max_tokens=2048)
    if "<end_of_turn>" in response_text:
        response_text = response_text.split("<end_of_turn>", 1)[0]
    return response_text


def chat_with_medgemma(
    chat_messages: list[dict],
    image_bytes: bytes | None,
    structure_names: list[str],
    educational_infos: list[dict],
) -> str:
    """Multi-turn Q&A chat using MedGemma, optionally with the X-ray image."""
    import base64

    context = []
    for i, name in enumerate(structure_names):
        info = educational_infos[i] if i < len(educational_infos) else {}
        context.append(f"- {name}: {info.get('description', '')} Clinical: {info.get('clinical_relevance', '')}")

    system_text = (
        "You are an expert medical educator specializing in radiology and anatomy. "
        "You help learners understand chest X-ray findings.\n\n"
        f"The current analysis involves these chest X-ray structures:\n"
        f"{chr(10).join(context)}\n\n"
        "Answer questions about these structures, the X-ray findings, related pathology, or radiology concepts. "
        "Keep answers focused and educational. Use markdown formatting. "
        "Always include a disclaimer that this is for educational purposes only.\n\n"
        "IMPORTANT: Always respond in Brazilian Portuguese (pt-BR)."
    )

    messages: list[dict] = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_text}],
        },
    ]

    # Build multi-turn conversation
    for i, msg in enumerate(chat_messages):
        role = "user" if msg["role"] == "user" else "assistant"
        content: list[dict] = [{"type": "text", "text": msg["content"]}]
        # Attach image to the first user message
        if role == "user" and i == 0 and image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            })
        messages.append({"role": role, "content": content})

    response_text = _call_medgemma(messages, max_tokens=2048)
    if "<end_of_turn>" in response_text:
        response_text = response_text.split("<end_of_turn>", 1)[0]
    return response_text


def suggest_questions_with_medgemma(
    image_bytes: bytes | None,
    structure_names: list[str],
    educational_infos: list[dict],
) -> list[str]:
    """Generate suggested questions based on the X-ray and identified structures."""
    import base64

    context = []
    for i, name in enumerate(structure_names):
        info = educational_infos[i] if i < len(educational_infos) else {}
        context.append(f"- {name}: {info.get('description', '')} Clinical: {info.get('clinical_relevance', '')}")

    prompt = f"""You are looking at a chest X-ray where the following structures have been identified:

{chr(10).join(context)}

Generate exactly 6 educational questions a medical student should ask about this specific X-ray. The questions should:
1. Be specific to what is visible on THIS image
2. Cover different learning angles: anatomy identification, normal vs abnormal, pathology correlation, clinical reasoning, and systematic approach
3. Be phrased as natural questions a student would ask

IMPORTANT: Write all questions in Brazilian Portuguese (pt-BR).

Output ONLY the 6 questions, one per line, numbered 1-6. No other text."""

    user_content: list[dict] = [{"type": "text", "text": prompt}]
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are an expert radiology educator. Output only the requested questions."}],
        },
        {"role": "user", "content": user_content},
    ]

    response_text = _call_medgemma(messages, max_tokens=512)
    if "<end_of_turn>" in response_text:
        response_text = response_text.split("<end_of_turn>", 1)[0]

    # Strip <thought>...</thought> blocks and find Final Answer if present
    import re
    cleaned = re.sub(r"<thought>.*?</thought>", "", response_text, flags=re.DOTALL | re.IGNORECASE)
    # Also handle unclosed thought tags
    if cleaned.strip().lower().startswith("<thought>") or cleaned.strip().lower().startswith("thought"):
        fa_idx = cleaned.find("Final Answer:")
        if fa_idx != -1:
            cleaned = cleaned[fa_idx + len("Final Answer:"):]
        else:
            # Try to find the numbered list after the thought block
            first_num = re.search(r"\n\s*1[.)]\s", cleaned)
            if first_num:
                cleaned = cleaned[first_num.start():]

    # Parse numbered lines
    questions = []
    for line in cleaned.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match "1. Question" or "1) Question" or "**1.** Question"
        match = re.match(r"^(?:\*\*)?(\d+)[.)]\*?\*?\s*(.+)$", line)
        if match:
            q = match.group(2).strip().strip("*").strip()
            if len(q) > 10:
                questions.append(q)
        elif line.endswith("?") and len(line) > 15 and not line.startswith("#"):
            questions.append(line)

    # If we got too few, use fallbacks
    if len(questions) < 3:
        names = ", ".join(structure_names)
        fallbacks = [
            f"Como o(a) {structure_names[0]} aparece neste Raio-X e está dentro dos limites normais?",
            f"Se este paciente tivesse pneumonia, como a aparência do(a) {structure_names[0]} mudaria?",
            "Qual é a relação cardiotorácica nesta imagem e o que ela indica?",
            "Pode me guiar por uma leitura sistemática ABCDE desta radiografia de tórax?",
            f"Quais são as patologias mais comuns que afetam o(a) {names}?",
        ]
        questions = questions + fallbacks[len(questions):]

    return questions[:6]


MOCK_BOUNDING_BOXES = {
    "right lung": [{"box_2d": [200, 80, 750, 470], "label": "right lung"}],
    "left lung": [{"box_2d": [200, 530, 750, 920], "label": "left lung"}],
    "heart": [{"box_2d": [350, 420, 700, 720], "label": "heart"}],
    "right clavicle": [{"box_2d": [140, 110, 340, 470], "label": "right clavicle"}],
    "left clavicle": [{"box_2d": [140, 530, 340, 890], "label": "left clavicle"}],
    "trachea": [{"box_2d": [50, 440, 300, 540], "label": "trachea"}],
    "aortic arch": [{"box_2d": [200, 420, 350, 560], "label": "aortic arch"}],
    "right costophrenic angle": [{"box_2d": [680, 50, 800, 200], "label": "right costophrenic angle"}],
    "left costophrenic angle": [{"box_2d": [680, 800, 800, 950], "label": "left costophrenic angle"}],
    "upper mediastinum": [{"box_2d": [100, 380, 350, 620], "label": "upper mediastinum"}],
    "right hilar structures": [{"box_2d": [300, 350, 500, 480], "label": "right hilar structures"}],
    "left hilar structures": [{"box_2d": [280, 520, 480, 650], "label": "left hilar structures"}],
    "spine": [{"box_2d": [200, 430, 800, 570], "label": "spine"}],
    "right hemidiaphragm": [{"box_2d": [650, 80, 780, 470], "label": "right hemidiaphragm"}],
    "left hemidiaphragm": [{"box_2d": [680, 530, 800, 920], "label": "left hemidiaphragm"}],
}


def mock_predict(object_name: str) -> tuple[str, list[dict]]:
    """Return mock bounding boxes for UI testing."""
    normalized = object_name.lower().strip()
    boxes = MOCK_BOUNDING_BOXES.get(normalized, [{"box_2d": [200, 200, 600, 600], "label": object_name}])
    import json
    response = f'The {object_name} is located in the expected anatomical position.\n\nFinal Answer: ```json{json.dumps(boxes)}```'
    return response, boxes


def get_educational_info(object_name: str) -> dict:
    """Get educational information about an anatomical structure."""
    normalized = object_name.lower().strip()
    if normalized in ANATOMY_INFO:
        return ANATOMY_INFO[normalized]
    # Partial match
    for key, info in ANATOMY_INFO.items():
        if normalized in key or key in normalized:
            return info
    return {
        "description": f"O(A) {object_name} é uma estrutura anatômica visível em radiografias de tórax.",
        "clinical_relevance": "Consulte referências de radiologia para informações clínicas detalhadas.",
    }
