import json
from typing import Any, Mapping
from app.domain.ports.ia_service import IIAService


class OpenAIAdapter(IIAService):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        schema = {
            "type": "object",
            "properties": {
                "puntaje": {"type": "number", "minimum": 0, "maximum": 100},
                "viabilidad": {"type": "string", "enum": ["ALTA", "MEDIA", "BAJA"]},
                "justificacion": {"type": "string"},
                "observaciones": {"type": "array", "items": {"type": "string"}},
                "recomendaciones": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["puntaje", "viabilidad", "justificacion", "observaciones", "recomendaciones"],
            "additionalProperties": False,
        }
        prompt = (
            "Evalua preliminarmente el siguiente proyecto municipal. "
            "Devuelve un dictamen técnico prudente y justificado.\n"
            f"Proyecto: {json.dumps(dict(proyecto), ensure_ascii=False)}"
        )
        response = await client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dictamen_municipal",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)
