import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(http_options=types.HttpOptions(timeout=120_000))  # lê GEMINI_API_KEY do ambiente
MODELO = "gemini-3.1-flash-lite"  # use o modelo Flash gratuito que o AI Studio mostrar

SYSTEM = """Você é um analista de QA sênior. Receberá a descrição de uma tarefa com critérios de aceite.
Gere casos de teste cobrindo cenários positivos, negativos e de borda.
Responda SOMENTE com JSON válido neste formato:
{"casos": [{"titulo": "...", "tipo": "positivo|negativo|borda", "criterio": "critério coberto", "gherkin": "Dado ...\\nQuando ...\\nEntão ..."}]}"""

SYSTEM_BASICO = """Gere casos de teste em Gherkin para a tarefa recebida.
Responda SOMENTE com JSON neste formato: {"casos": [{"titulo": "...", "tipo": "positivo|negativo|borda", "criterio": "...", "gherkin": "Dado ...\\nQuando ...\\nEntão ..."}]}"""

def gerar_casos(tarefa: str, system: str = SYSTEM) -> list[dict]:
    resp = client.models.generate_content(
        model=MODELO,
        contents=tarefa,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        ),
    )
    texto = resp.text.strip()
    texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)["casos"]

