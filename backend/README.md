# PMV - Sistema Multiagente para Priorización de Proyectos de Inversión Municipal

Scaffold inicial basado en la arquitectura hexagonal definida por el grupo.

## Alcance actual

- FastAPI y endpoint `/health`.
- Registro temporal de proyectos en memoria.
- Puerto `IIAService` desacoplado de proveedores.
- Adaptadores OpenAI y Gemini.
- `AIProviderFactory` y fallback entre proveedores.
- LangGraph mínimo: Coordinador -> Técnico.
- Esquema Pydantic para dictamen estructurado.
- Puerto `IRetrievalService` y stub de Qdrant preparado para PMV2.
- Pruebas unitarias sin consumo de APIs reales.

## No incluido todavía

- Persistencia real con PostgreSQL/SQLAlchemy/Alembic.
- Los seis agentes completos.
- RAG con corpus normativo.
- HITL/checkpoints.
- Celery + Redis.
- LangSmith.

## Ejecución local

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger: http://localhost:8000/docs

## Probar Gemini sin costo inicial

En `.env`:

```env
AI_PROVIDER=gemini
AI_FALLBACK_PROVIDER=openai
GEMINI_API_KEY=TU_CLAVE
OPENAI_API_KEY=
```

Si no se configura ninguna API key, los tests siguen siendo ejecutables porque usan mocks/stubs y no deben consumir servicios reales.

## Flujo PMV

Proyecto municipal -> FastAPI -> Caso de uso -> IIAService -> LangGraph -> Proveedor IA -> Dictamen JSON -> REST

## Próximos pasos del grupo

1. Conectar repositorio PostgreSQL real.
2. Vincular el endpoint de evaluación al identificador persistido del proyecto.
3. Completar agentes Económico, Jurídico, Social y Ambiental.
4. Integrar Qdrant y corpus normativo.
5. Implementar HITL/checkpoints.
6. Incorporar Celery + Redis desde PMV2.
