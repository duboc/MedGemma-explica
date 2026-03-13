"""CT Findings Report: Parse MedGemma CT analysis into structured JSON via Gemini Flash."""

import json
import logging
import re

logger = logging.getLogger(__name__)

CT_STRUCTURE_PROMPT = """Converta esta analise de TC em JSON estruturado.
A entrada e uma analise bruta de tomografia computadorizada.

ENTRADA:
{raw_text}

REGIAO ANATOMICA: {body_part}

Retorne APENAS JSON valido (sem markdown fences), seguindo este esquema exato:
{{
  "tecnica": {{
    "tipo_exame": "ex: TC de abdome com contraste, fase arterial",
    "plano": "ex: Axial com reconstrucoes multiplanares",
    "espessura": "ex: 2.5mm",
    "contraste": "com contraste | sem contraste",
    "observacoes": "outras observacoes tecnicas"
  }},
  "achados": [
    {{
      "regiao": "ex: Rins, Figado, Parenquima Pulmonar",
      "status": "normal | alterado | inconclusivo",
      "descricao": "descricao detalhada dos achados nesta regiao",
      "subitens": [
        {{
          "estrutura": "ex: Rim direito",
          "achado": "descricao especifica do achado",
          "medidas": "medidas quando disponiveis, ex: 4.1 x 4.3 cm",
          "relevancia": "alta | media | baixa"
        }}
      ]
    }}
  ],
  "impressao": [
    {{
      "numero": 1,
      "descricao": "achado principal em ordem de relevancia",
      "gravidade": "critico | importante | menor | normal"
    }}
  ],
  "diferenciais": [
    {{
      "achado": "achado para o qual se listam diferenciais",
      "opcoes": ["diagnostico diferencial 1", "diagnostico diferencial 2", "diagnostico diferencial 3"]
    }}
  ],
  "recomendacoes": [
    {{
      "tipo": "exame | acompanhamento | encaminhamento | laboratorio",
      "descricao": "recomendacao especifica",
      "urgencia": "imediata | breve | eletiva"
    }}
  ]
}}

Regras:
- Extraia TODAS as informacoes da analise fornecida
- Inclua pelo menos 3-5 regioes em achados, cada uma com subitens
- Inclua todas as impressoes diagnosticas mencionadas na analise
- Para achados significativos, inclua diagnosticos diferenciais
- Inclua recomendacoes praticas e especificas
- Classifique a gravidade: critico (requer acao imediata), importante (requer acompanhamento), menor (achado incidental), normal (sem patologia)
- Se a analise menciona achados normais, inclua como status "normal" sem diferenciais
- ESCREVA TODO o conteudo em portugues brasileiro (pt-BR). Mantenha as chaves JSON em ingles."""


def parse_ct_report(raw_text: str, body_part: str) -> dict:
    """Send MedGemma CT analysis to Gemini Flash for JSON structuring."""
    from gemini_flash import _call_gemini

    prompt = CT_STRUCTURE_PROMPT.format(raw_text=raw_text, body_part=body_part)
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    response = _call_gemini(
        contents,
        system_instruction="Voce e um formatador de dados medicos. Retorne APENAS JSON valido, sem markdown fences.",
        response_mime_type="application/json",
        max_output_tokens=4096,
    )

    # Extract JSON
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        response = response[start:end]

    result = json.loads(response)
    result["disclaimer"] = (
        "Esta analise e apenas para fins educacionais e nao deve ser "
        "utilizada para diagnostico clinico. Sempre consulte um profissional de saude qualificado."
    )
    return result


def mock_ct_report(body_part: str, raw_text: str) -> dict:
    """Return structured mock report based on body part."""
    return _MOCK_REPORTS.get(body_part, _build_generic_mock(body_part, raw_text))


def _build_generic_mock(body_part: str, raw_text: str) -> dict:
    """Build a minimal structured report from raw text."""
    return {
        "tecnica": {
            "tipo_exame": f"TC de {body_part.lower()}",
            "plano": "Axial",
            "espessura": "N/A",
            "contraste": "N/A",
            "observacoes": "",
        },
        "achados": [
            {
                "regiao": body_part,
                "status": "normal",
                "descricao": "Avaliacao demonstrativa sem achados patologicos significativos.",
                "subitens": [],
            }
        ],
        "impressao": [
            {"numero": 1, "descricao": f"TC de {body_part.lower()} dentro dos limites da normalidade.", "gravidade": "normal"}
        ],
        "diferenciais": [],
        "recomendacoes": [
            {"tipo": "acompanhamento", "descricao": "Correlacionar com dados clinicos.", "urgencia": "eletiva"}
        ],
        "disclaimer": "Esta analise e apenas para fins educacionais.",
    }


_MOCK_REPORTS = {
    "Torax": {
        "tecnica": {
            "tipo_exame": "TC de torax sem contraste endovenoso",
            "plano": "Axial com reconstrucoes em janela pulmonar e mediastinal",
            "espessura": "1mm",
            "contraste": "sem contraste",
            "observacoes": "Adquirida em inspiracao profunda",
        },
        "achados": [
            {
                "regiao": "Parenquima Pulmonar",
                "status": "normal",
                "descricao": "Parenquima pulmonar com atenuacao preservada bilateralmente. Fissuras integras.",
                "subitens": [
                    {"estrutura": "Pulmao direito", "achado": "Atenuacao preservada nos tres lobos. Sem consolidacoes, opacidades em vidro fosco ou nodulos.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Pulmao esquerdo", "achado": "Parenquima homogeneo nos lobos superior e inferior. Sem massas ou areas de aprisionamento aereo.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Vias aereas", "achado": "Traqueia na linha media, calibre normal. Bronquios principais e lobares pervios.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Mediastino",
                "status": "normal",
                "descricao": "Sem linfonodomegalias mediastinais ou hilares significativas.",
                "subitens": [
                    {"estrutura": "Linfonodos", "achado": "Sem linfonodomegalias (< 10mm no menor eixo).", "medidas": "< 10mm", "relevancia": "baixa"},
                    {"estrutura": "Grandes vasos", "achado": "Aorta com calibre e trajeto normais. Arteria pulmonar sem dilatacao.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Coracao", "achado": "Silhueta cardiaca de dimensoes normais. Sem derrame pericardico.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Parede Toracica",
                "status": "normal",
                "descricao": "Estruturas osseas e tecidos moles sem alteracoes.",
                "subitens": [
                    {"estrutura": "Estruturas osseas", "achado": "Sem lesoes liticas ou blasticas.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Espaco pleural", "achado": "Sem derrame pleural bilateral.", "medidas": "", "relevancia": "baixa"},
                ],
            },
        ],
        "impressao": [
            {"numero": 1, "descricao": "TC de torax dentro dos limites da normalidade.", "gravidade": "normal"},
            {"numero": 2, "descricao": "Ausencia de nodulos pulmonares, consolidacoes ou massas.", "gravidade": "normal"},
            {"numero": 3, "descricao": "Sem linfonodomegalias mediastinais ou hilares.", "gravidade": "normal"},
        ],
        "diferenciais": [],
        "recomendacoes": [
            {"tipo": "acompanhamento", "descricao": "Correlacionar com dados clinicos e indicacao do exame.", "urgencia": "eletiva"},
            {"tipo": "acompanhamento", "descricao": "Em pacientes de alto risco, considerar acompanhamento conforme Lung-RADS.", "urgencia": "eletiva"},
        ],
        "disclaimer": "Esta analise e apenas para fins educacionais.",
    },
    "Abdome": {
        "tecnica": {
            "tipo_exame": "TC de abdome com contraste endovenoso",
            "plano": "Axial com reconstrucoes multiplanares",
            "espessura": "2.5mm",
            "contraste": "com contraste",
            "observacoes": "Fase arterial",
        },
        "achados": [
            {
                "regiao": "Rins",
                "status": "alterado",
                "descricao": "Lesao solida no rim direito com realce heterogeneo. Multiplos calculos renais a direita.",
                "subitens": [
                    {"estrutura": "Rim direito - massa", "achado": "Lesao solida no polo inferior com realce heterogeneo na fase arterial. Contornos parcialmente irregulares, sem extensao para gordura perirrenal.", "medidas": "4.1 x 4.3 cm", "relevancia": "alta"},
                    {"estrutura": "Rim direito - calculos", "achado": "Multiplas calcificacoes no grupo calicial inferior, compativeis com litiase renal.", "medidas": "", "relevancia": "media"},
                    {"estrutura": "Rim esquerdo", "achado": "Dimensoes, contornos e atenuacao normais. Boa diferenciacao cortico-medular. Sistema coletor nao dilatado.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Figado e Vias Biliares",
                "status": "normal",
                "descricao": "Figado de dimensoes e contornos normais, com atenuacao homogenea.",
                "subitens": [
                    {"estrutura": "Figado", "achado": "Dimensoes e contornos normais. Sem lesoes focais hepaticas.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Vesicula e vias biliares", "achado": "Normodistendida, sem calculos. Vias biliares de calibre normal.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Baco, Pancreas e Adrenais",
                "status": "normal",
                "descricao": "Orgaos solidos abdominais de aspecto habitual.",
                "subitens": [
                    {"estrutura": "Baco", "achado": "Homogeneo, dimensoes normais.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Pancreas", "achado": "Morfologia e atenuacao preservadas, sem dilatacao ductal.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Adrenais", "achado": "Aspecto habitual bilateralmente.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Estruturas Vasculares",
                "status": "normal",
                "descricao": "Aorta abdominal de calibre normal. Sem linfonodomegalias retroperitoneais.",
                "subitens": [
                    {"estrutura": "Aorta abdominal", "achado": "Calibre normal, sem aneurismas ou disseccoes.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Parede Abdominal",
                "status": "alterado",
                "descricao": "Hernia umbilical com conteudo gorduroso.",
                "subitens": [
                    {"estrutura": "Hernia umbilical", "achado": "Hernia contendo gordura, sem sinais de encarceramento.", "medidas": "", "relevancia": "baixa"},
                ],
            },
        ],
        "impressao": [
            {"numero": 1, "descricao": "Massa renal direita (4.1 x 4.3 cm) com realce heterogeneo, altamente suspeita para carcinoma de celulas renais.", "gravidade": "critico"},
            {"numero": 2, "descricao": "Litiase renal a direita (multiplos calculos caliciais inferiores).", "gravidade": "importante"},
            {"numero": 3, "descricao": "Hernia umbilical contendo gordura, sem complicacoes.", "gravidade": "menor"},
        ],
        "diferenciais": [
            {
                "achado": "Massa renal direita",
                "opcoes": [
                    "Carcinoma de celulas renais (subtipo celulas claras)",
                    "Oncocitoma renal",
                    "Angiomiolipoma pobre em gordura",
                    "Metastase renal",
                ],
            },
            {
                "achado": "Calcificacoes renais",
                "opcoes": [
                    "Litiase por oxalato de calcio",
                    "Nefrocalcinose focal",
                    "Calcificacao papilar",
                ],
            },
        ],
        "recomendacoes": [
            {"tipo": "encaminhamento", "descricao": "Encaminhamento para urologia para avaliacao da massa renal. Considerar nefrectomia parcial vs radical.", "urgencia": "breve"},
            {"tipo": "exame", "descricao": "RM dos rins para melhor caracterizacao da lesao e planejamento cirurgico.", "urgencia": "breve"},
            {"tipo": "laboratorio", "descricao": "Avaliacao laboratorial: funcao renal (creatinina, TFG), hemograma, LDH, calcio.", "urgencia": "breve"},
            {"tipo": "exame", "descricao": "TC de torax para estadiamento, caso confirmada neoplasia renal.", "urgencia": "breve"},
            {"tipo": "acompanhamento", "descricao": "Acompanhamento da litiase renal conforme sintomas.", "urgencia": "eletiva"},
        ],
        "disclaimer": "Esta analise e apenas para fins educacionais.",
    },
    "Cranio": {
        "tecnica": {
            "tipo_exame": "TC de cranio sem contraste endovenoso",
            "plano": "Coronal com reconstrucoes multiplanares",
            "espessura": "2.5mm",
            "contraste": "sem contraste",
            "observacoes": "",
        },
        "achados": [
            {
                "regiao": "Parenquima Cerebral",
                "status": "normal",
                "descricao": "Hemisferios cerebrais com atenuacao normal e simetrica.",
                "subitens": [
                    {"estrutura": "Hemisferios cerebrais", "achado": "Atenuacao normal e simetrica. Diferenciacao substancia branca/cinzenta preservada.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Fossa posterior", "achado": "Cerebelo e tronco encefalico de morfologia e atenuacao normais.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Linha media", "achado": "Estruturas centradas, sem desvios.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Sistema Ventricular",
                "status": "normal",
                "descricao": "Ventriculos laterais simetricos, de dimensoes normais. Sem hidrocefalia.",
                "subitens": [
                    {"estrutura": "Ventriculos laterais", "achado": "Simetricos, dimensoes normais para a faixa etaria.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "III e IV ventriculos", "achado": "Aspecto habitual, sem sinais de hidrocefalia.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Cisternas basais", "achado": "Pervias.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Estruturas Extra-axiais",
                "status": "normal",
                "descricao": "Sem colecoes extra-axiais ou hemorragias.",
                "subitens": [
                    {"estrutura": "Espacos subaracnoideos", "achado": "Compativeis com a faixa etaria.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Hematomas", "achado": "Ausencia de hematoma subdural, epidural ou hemorragia subaracnoidea.", "medidas": "", "relevancia": "baixa"},
                ],
            },
            {
                "regiao": "Estruturas Osseas",
                "status": "normal",
                "descricao": "Calota craniana integra. Seios paranasais pneumatizados.",
                "subitens": [
                    {"estrutura": "Calota craniana", "achado": "Integra, sem fraturas ou lesoes liticas/blasticas.", "medidas": "", "relevancia": "baixa"},
                    {"estrutura": "Seios paranasais", "achado": "Pneumatizacao normal.", "medidas": "", "relevancia": "baixa"},
                ],
            },
        ],
        "impressao": [
            {"numero": 1, "descricao": "TC de cranio sem evidencias de lesoes intracranianas agudas.", "gravidade": "normal"},
            {"numero": 2, "descricao": "Ausencia de hemorragias, efeito de massa ou desvio de linha media.", "gravidade": "normal"},
            {"numero": 3, "descricao": "Sistema ventricular de dimensoes normais.", "gravidade": "normal"},
        ],
        "diferenciais": [],
        "recomendacoes": [
            {"tipo": "acompanhamento", "descricao": "Correlacionar com dados clinicos e exame neurologico.", "urgencia": "eletiva"},
            {"tipo": "exame", "descricao": "RM do encefalo indicada para investigacao mais detalhada, quando TC e normal e persistem sintomas.", "urgencia": "eletiva"},
            {"tipo": "exame", "descricao": "Angio-TC ou angio-RM se suspeita de patologia vascular.", "urgencia": "eletiva"},
        ],
        "disclaimer": "Esta analise e apenas para fins educacionais.",
    },
}
