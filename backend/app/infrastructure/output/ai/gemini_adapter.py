import json
from typing import Any, Mapping
from app.domain.ports.ia_service import IIAService


class GeminiAdapter(IIAService):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        prompt = (
            "Evalua preliminarmente el siguiente proyecto de inversion municipal. "
            "Responde exclusivamente en JSON con: puntaje (0-100), viabilidad "
            "(ALTA|MEDIA|BAJA), justificacion, observaciones[], recomendaciones[].\n"
            f"Proyecto: {json.dumps(dict(proyecto), ensure_ascii=False)}"
        )
        response = await client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
