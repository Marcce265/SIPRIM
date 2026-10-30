from __future__ import annotations

import os
import socket
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, ClassVar, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import jwt
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.application.dto.pmv1_dto import PMV1ProjectCreate
from backend.domain.exceptions.pmv1_exceptions import (
    ConfiguracionPMV1Error,
    CredencialesInvalidasError,
    ExpedientePMV1IncompletoError,
    RecursoPMV1NoEncontradoError,
    ServicioNoDisponibleError,
)


def _dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


_EXPEDIENTE_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _allocate_expediente_code(conn: psycopg.Connection[Any]) -> str:
    """Código legible único para búsqueda rápida (EXP- + 6 caracteres)."""
    for _ in range(12):
        suffix = "".join(
            secrets.choice(_EXPEDIENTE_CODE_ALPHABET) for _ in range(6)
        )
        code = f"EXP-{suffix}"
        exists = conn.execute(
            "SELECT 1 FROM projects WHERE upper(code) = upper(%s)", (code,)
        ).fetchone()
        if not exists:
            return code
    raise ConfiguracionPMV1Error("No se pudo generar un código de expediente único")


class TaskDispatcher(Protocol):
    def dispatch_economic(self, payload: dict[str, Any]) -> None: ...


def _is_db_available(url: str) -> bool:
    try:
        if "@" in url:
            host_port = url.split("@", 1)[1].split("/", 1)[0]
            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host, port = host_port, 5432
        else:
            host, port = "127.0.0.1", 5432
        if host in ("localhost", "127.0.0.1"):
            host = "127.0.0.1"
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except Exception:
        return False


def _load_fallback_seed_documents() -> list[dict[str, Any]]:
    seed_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "database", "platform_db", "02_seed.sql"
    )
    if not os.path.exists(seed_path):
        return []
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            text = f.read()
        idx = text.find("INSERT INTO normative_documents")
        idx_end = text.find("ON CONFLICT (id)", idx)
        if idx == -1 or idx_end == -1:
            return []
        block = text[idx:idx_end]
        tuples = re.findall(
            r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'((?:''|[^'])*)'\s*,\s*(TRUE|FALSE)\s*,\s*(TRUE|FALSE)\s*,\s*'([^']+)'\s*\)",
            block,
        )
        docs = []
        for t in tuples:
            docs.append({
                "id": t[0],
                "document_name": t[1],
                "short_code": t[2],
                "version": t[3],
                "topic": t[4],
                "content": t[5].replace("''", "'"),
                "in_force": t[6] == "TRUE",
                "has_alert": t[7] == "TRUE",
                "data_origin": t[8],
            })
        return docs
    except Exception:
        return []


class AuthService:
    def __init__(
        self,
        db_url: str,
        jwt_secret: str,
        issuer: str,
        audience: str,
        expiration_minutes: int,
    ) -> None:
        self.db_url = _dsn(db_url)
        self.jwt_secret = jwt_secret
        self.issuer = issuer
        self.audience = audience
        self.expiration_minutes = expiration_minutes
        self.password_hasher = PasswordHasher()

    def issue_token(
        self,
        user_id: UUID,
        roles: list[str],
        full_name: str = "",
    ) -> dict[str, Any]:
        """Emite una sesion con token JWT firmado a partir de identidad verificada o autorizada."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.expiration_minutes)
        claims = {
            "sub": str(user_id),
            "roles": list(roles),
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "exp": expires,
        }
        token = jwt.encode(claims, self.jwt_secret, algorithm="HS256")
        return {
            "access_token": token,
            "expires_in": self.expiration_minutes * 60,
            "user_id": user_id,
            "full_name": full_name,
            "roles": list(roles),
        }

    def login(self, email: str, password: str) -> dict[str, Any]:
        clean_email = email.strip().lower()
        try:
            if not _is_db_available(self.db_url):
                raise psycopg.OperationalError("Base de datos de autenticacion no disponible")
            with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
                row = conn.execute(
                    """
                    SELECT u.id, u.full_name, u.password_hash, u.is_active,
                           COALESCE(array_agg(r.code) FILTER (WHERE r.code IS NOT NULL), '{}') AS roles
                    FROM users u
                    LEFT JOIN user_roles ur ON ur.user_id = u.id
                    LEFT JOIN roles r ON r.id = ur.role_id
                    WHERE u.email = %s
                    GROUP BY u.id
                    """,
                    (clean_email,),
                ).fetchone()
            if not row or not row["is_active"]:
                raise CredencialesInvalidasError("Credenciales invalidas")
            try:
                self.password_hasher.verify(row["password_hash"], password)
            except (VerifyMismatchError, InvalidHashError):
                raise CredencialesInvalidasError("Credenciales invalidas") from None
            return self.issue_token(row["id"], row["roles"], row["full_name"])
        except psycopg.OperationalError as err:
            raise ServicioNoDisponibleError(
                "Servicio de autenticacion no disponible: la base de datos no responde."
            ) from err

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                issuer=self.issuer,
                audience=self.audience,
            )
        except jwt.PyJWTError as exc:
            raise CredencialesInvalidasError("Token invalido o expirado") from exc



class NormativeSearchEngine:
    """Motor de ponderacion de relevancia para consultas normativas referenciales (HU2.1 / RF12)."""

    @classmethod
    def resolve_location(cls, chunk: dict[str, Any]) -> str:
        """Extrae o resuelve la ubicacion identificable (articulo, seccion o ID estable) de un fragmento."""
        topic = str(chunk.get("topic", ""))
        text_content = str(chunk.get("content", ""))
        chunk_id = str(chunk.get("id", ""))
        # 1. Referencia explicita entre parentesis en el tema (Art., Titulo, Reglamento, etc.)
        m_topic = re.search(
            r"\(([^)]*(?:Art|Título|Titulo|Reglamento|RNE|SINAGERD|Sección|Seccion|Ley DUS|Índice|Indice)[^)]*)\)",
            topic,
            re.IGNORECASE,
        )
        if m_topic:
            return m_topic.group(1).strip()
        # 2. Articulo explicito al inicio del contenido
        m_content = re.match(r"^(Art(?:[ií]culo)?\.\s*\d+[^\.\-\:]*)", text_content, re.IGNORECASE)
        if m_content:
            return m_content.group(1).strip()
        # 3. Identificador estable del fragmento como garantia de localizacion
        return f"Fragmento ID {chunk_id}"

    STOP_WORDS: ClassVar[set[str]] = {
        "a", "al", "ante", "bajo", "cabe", "como", "con", "contra", "de", "del",
        "desde", "el", "ella", "ellas", "ellos", "en", "entre", "es", "esa", "esas",
        "ese", "esos", "esta", "estas", "este", "estos", "fue", "fueron", "hacia",
        "hasta", "la", "las", "le", "les", "lo", "los", "me", "mi", "mis", "muy",
        "nos", "nosotros", "o", "para", "pero", "por", "que", "qué", "se", "según",
        "sin", "so", "sobre", "son", "su", "sus", "te", "ti", "tu", "tus", "un",
        "una", "unas", "unos", "y", "ya"
    }

    @classmethod
    def extract_keywords(cls, query: str) -> list[str]:
        words = re.findall(r"[\wáéíóúüñ]+", query.lower())
        return [w for w in words if len(w) > 1 and w not in cls.STOP_WORDS]

    @classmethod
    def score_chunk(cls, chunk: dict[str, Any], query: str, keywords: list[str]) -> float:
        score = 0.0
        q_lower = query.lower()
        id_lower = str(chunk.get("id", "")).lower()
        topic_lower = str(chunk.get("topic", "")).lower()
        content_lower = str(chunk.get("content", "")).lower()
        doc_lower = str(chunk.get("document_name", "")).lower()
        code_lower = str(chunk.get("short_code", "")).lower()

        # Coincidencia directa por id (ej: "PDUPDM-02", "LEY27972-01")
        if id_lower and (id_lower in q_lower or q_lower in id_lower):
            score += 50.0

        # Coincidencia de frase completa
        if q_lower in topic_lower:
            score += 35.0
        if q_lower in content_lower:
            score += 25.0
        if q_lower in doc_lower or q_lower in code_lower:
            score += 15.0

        # Coincidencias por palabra clave
        for kw in keywords:
            if kw in id_lower:
                score += 20.0
            if kw in topic_lower:
                score += 15.0
            if kw in content_lower:
                score += 5.0
            if kw in doc_lower or kw in code_lower:
                score += 4.0

        # Ponderacion de alertas si la consulta alude a temas de riesgo/suelo/incompatibilidad
        alert_terms = {"alerta", "riesgo", "incompatible", "incompatibilidad", "conflicto", "vulnera", "suelo", "zonificacion", "proteccion"}
        if chunk.get("has_alert") and any(at in q_lower for at in alert_terms):
            score += 20.0

        return round(score, 2)


class PlatformService:
    def __init__(
        self,
        db_url: str,
        dispatcher: TaskDispatcher,
        enable_demo_fallback: bool = False,
    ) -> None:
        self.db_url = _dsn(db_url)
        self.dispatcher = dispatcher
        self.enable_demo_fallback = enable_demo_fallback

    @staticmethod
    def _missing(data: PMV1ProjectCreate) -> list[str]:
        values = {
            "title": data.title,
            "description": data.description,
            "location": data.location,
            "proposed_land_use": data.proposed_land_use,
            "estimated_budget_pen": data.estimated_budget_pen,
            "beneficiaries_count": data.beneficiaries_count,
        }
        missing = [name for name, value in values.items() if value is None]
        if data.estimated_budget_pen is not None and data.estimated_budget_pen <= 0:
            missing.append("estimated_budget_pen (> 0)")
        if data.beneficiaries_count is not None and data.beneficiaries_count <= 0:
            missing.append("beneficiaries_count (> 0)")
        return missing

    def create_project(self, data: PMV1ProjectCreate, actor_id: UUID) -> dict[str, Any]:
        missing = self._missing(data)
        if missing:
            raise ExpedientePMV1IncompletoError(missing)
        project_id, version_id = uuid4(), uuid4()
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
                code = (data.code or "").strip() or _allocate_expediente_code(conn)
                conn.execute(
                    "INSERT INTO projects (id, code, created_by_user_id, status) VALUES (%s,%s,%s,'ready')",
                    (project_id, code, actor_id),
                )
                conn.execute(
                    """
                    INSERT INTO project_versions
                    (id, project_id, version_number, title, description,
                     location_description, proposed_land_use, territorial_data_origin,
                     estimated_budget_pen, beneficiaries_count, created_by_user_id)
                    VALUES (%s,%s,1,%s,%s,%s,%s,'declared',%s,%s,%s)
                    """,
                    (
                        version_id,
                        project_id,
                        data.title,
                        data.description,
                        data.location,
                        data.proposed_land_use,
                        data.estimated_budget_pen,
                        data.beneficiaries_count,
                        actor_id,
                    ),
                )
                conn.execute(
                    """INSERT INTO audit_events
                    (actor_user_id, action, entity_type, entity_id, details)
                    VALUES (%s,'PROJECT_CREATED','project',%s,%s)""",
                    (
                        actor_id,
                        project_id,
                        Jsonb({"project_version_id": str(version_id)}),
                    ),
                )
        return self.get_project(project_id)

    def get_project(self, project_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT p.id AS project_id, pv.id AS project_version_id, p.code,
                       pv.version_number, p.status, pv.title, pv.description,
                       pv.location_description AS location, pv.proposed_land_use,
                       pv.territorial_data_origin,
                       pv.estimated_budget_pen, pv.beneficiaries_count
                FROM projects p JOIN project_versions pv ON pv.project_id = p.id
                WHERE p.id=%s ORDER BY pv.version_number DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if not row:
            raise RecursoPMV1NoEncontradoError("Proyecto no encontrado")
        return dict(row)

    def get_project_by_code(self, code: str) -> dict[str, Any]:
        normalized = code.strip()
        if len(normalized) < 3:
            raise RecursoPMV1NoEncontradoError("Código de expediente no válido")
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "SELECT id FROM projects WHERE upper(code) = upper(%s)",
                (normalized,),
            ).fetchone()
        if not row:
            raise RecursoPMV1NoEncontradoError(
                f"No existe expediente con código {normalized}"
            )
        return self.get_project(row["id"])

    def validate_project(self, project_id: UUID) -> dict[str, Any]:
        project = self.get_project(project_id)
        missing = [
            field
            for field in (
                "title",
                "description",
                "location",
                "proposed_land_use",
                "estimated_budget_pen",
                "beneficiaries_count",
            )
            if project.get(field) in (None, "")
        ]
        complete = not missing
        return {
            "complete": complete,
            "status": "ready" if complete else "incomplete",
            "missing_fields": missing,
            "message": "Expediente completo"
            if complete
            else "Complete los datos antes de evaluar",
        }

    def request_evaluation(
        self, project_version_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
                previous = conn.execute(
                    """SELECT e.id AS evaluation_id, e.status, o.id AS event_id, o.payload,
                              o.published_at IS NULL AS publication_pending
                       FROM evaluations e JOIN outbox_events o ON o.aggregate_id=e.id
                       WHERE e.idempotency_key=%s""",
                    (idempotency_key,),
                ).fetchone()
                if previous:
                    previous = dict(previous)
                    previous["duplicated"] = True
                    return previous

                snapshot = conn.execute(
                    """
                    SELECT pv.id AS project_version_id, pv.project_id, pv.estimated_budget_pen,
                           pv.beneficiaries_count, cv.id AS criteria_version_id,
                           cv.version_number AS criteria_version_number,
                           cv.excellent_cost_pen, cv.unacceptable_cost_pen
                    FROM project_versions pv CROSS JOIN criteria_versions cv
                    WHERE pv.id=%s AND cv.status='active'
                    """,
                    (project_version_id,),
                ).fetchone()
                if not snapshot:
                    raise RecursoPMV1NoEncontradoError(
                        "Version de proyecto o criterios activos no encontrados"
                    )
                evaluation_id, event_id = uuid4(), uuid4()
                payload = {
                    "event_id": str(event_id),
                    "event_type": "EconomicEvaluationRequested",
                    "evaluation_id": str(evaluation_id),
                    "project_version_id": str(snapshot["project_version_id"]),
                    "criteria_version_id": str(snapshot["criteria_version_id"]),
                    "budget_pen": str(snapshot["estimated_budget_pen"]),
                    "beneficiaries_count": snapshot["beneficiaries_count"],
                    "excellent_cost_pen": str(snapshot["excellent_cost_pen"]),
                    "unacceptable_cost_pen": str(snapshot["unacceptable_cost_pen"]),
                    "criteria_version_number": snapshot["criteria_version_number"],
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": str(evaluation_id),
                    "schema_version": 1,
                }
                conn.execute(
                    """INSERT INTO evaluations
                    (id, project_version_id, criteria_version_id, requested_by_user_id,
                     status, idempotency_key) VALUES (%s,%s,%s,%s,'queued',%s)""",
                    (
                        evaluation_id,
                        project_version_id,
                        snapshot["criteria_version_id"],
                        actor_id,
                        idempotency_key,
                    ),
                )
                conn.execute(
                    "INSERT INTO outbox_events (id,event_type,aggregate_id,payload) VALUES (%s,'EconomicEvaluationRequested',%s,%s)",
                    (event_id, evaluation_id, Jsonb(payload)),
                )
                conn.execute(
                    "UPDATE projects SET status='evaluating', updated_at=now() WHERE id=%s",
                    (snapshot["project_id"],),
                )
                conn.execute(
                    """INSERT INTO audit_events
                    (actor_user_id,action,entity_type,entity_id,details)
                    VALUES (%s,'EVALUATION_QUEUED','evaluation',%s,%s)""",
                    (actor_id, evaluation_id, Jsonb({"event_id": str(event_id)})),
                )

        publication_pending = False
        try:
            self.dispatcher.dispatch_economic(payload)
            with psycopg.connect(self.db_url) as conn:
                conn.execute(
                    "UPDATE outbox_events SET published_at=now(), publish_attempts=publish_attempts+1 WHERE id=%s",
                    (event_id,),
                )
        except Exception:
            publication_pending = True
            with psycopg.connect(self.db_url) as conn:
                conn.execute(
                    "UPDATE outbox_events SET publish_attempts=publish_attempts+1 WHERE id=%s",
                    (event_id,),
                )
        return {
            "evaluation_id": evaluation_id,
            "event_id": event_id,
            "status": "queued",
            "duplicated": False,
            "publication_pending": publication_pending,
        }

    def get_evaluation(self, evaluation_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT e.id AS evaluation_id,e.project_version_id,e.criteria_version_id,e.status,
                       r.economic_assessment_id,r.cost_per_beneficiary_pen,r.score_0_100,
                       r.explanation,r.algorithm_version
                FROM evaluations e LEFT JOIN economic_result_projections r ON r.evaluation_id=e.id
                WHERE e.id=%s
                """,
                (evaluation_id,),
            ).fetchone()
        if not row:
            raise RecursoPMV1NoEncontradoError("Evaluacion no encontrada")
        result = None
        if row["economic_assessment_id"]:
            result = {
                "economic_assessment_id": row["economic_assessment_id"],
                "cost_per_beneficiary_pen": row["cost_per_beneficiary_pen"],
                "score_0_100": row["score_0_100"],
                "explanation": row["explanation"],
                "algorithm_version": row["algorithm_version"],
            }
        return {
            "evaluation_id": row["evaluation_id"],
            "project_version_id": row["project_version_id"],
            "criteria_version_id": row["criteria_version_id"],
            "status": row["status"],
            "result": result,
        }

    def record_legal_abstention(self, project_id: UUID, actor_id: UUID) -> None:
        self.get_project(project_id)
        with psycopg.connect(self.db_url) as conn:
            conn.execute(
                """INSERT INTO audit_events
                (actor_user_id,action,entity_type,entity_id,details)
                VALUES (%s,'LEGAL_PRECHECK_REQUIRES_REVIEW','project',%s,%s)""",
                (actor_id, project_id, Jsonb({"reason": "no_versioned_legal_corpus"})),
            )

    def request_zoning_precheck(
        self, project_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        """Registra una alerta territorial sin fabricar compatibilidad PDU/PDM."""

        if not idempotency_key.strip():
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")
        project = self.get_project(project_id)
        missing = [
            field
            for field in ("location", "proposed_land_use")
            if not project.get(field)
        ]
        if missing:
            raise ExpedientePMV1IncompletoError(missing)

        limitations = (
            "No existe un corpus PDU/PDM oficial, versionado y activo ni una capa GIS "
            "que permita ubicar el predio. La solicitud no equivale a conformidad territorial."
        )
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
                previous = conn.execute(
                    """
                    SELECT id AS review_id, project_version_id, status,
                           compatible, limitations
                    FROM zoning_review_requests WHERE idempotency_key=%s
                    """,
                    (idempotency_key,),
                ).fetchone()
                if previous:
                    if previous["project_version_id"] != project["project_version_id"]:
                        raise ConfiguracionPMV1Error(
                            "Idempotency-Key ya fue utilizada para otro expediente"
                        )
                    previous_data = dict(previous)
                    previous_data.pop("project_version_id")
                    return {
                        **previous_data,
                        "project_id": project["project_id"],
                        "project_version_id": project["project_version_id"],
                        "location": project["location"],
                        "proposed_land_use": project["proposed_land_use"],
                        "territorial_data_origin": project["territorial_data_origin"],
                        "evidence": [],
                        "alerts": [
                            "No se puede concluir compatibilidad sin evidencia territorial versionada."
                        ],
                        "requires_human_review": True,
                        "duplicated": True,
                    }

                review_id = uuid4()
                conn.execute(
                    """
                    INSERT INTO zoning_review_requests
                    (id,project_version_id,requested_by_user_id,idempotency_key,
                     status,compatible,limitations)
                    VALUES (%s,%s,%s,%s,'requires_review',NULL,%s)
                    """,
                    (
                        review_id,
                        project["project_version_id"],
                        actor_id,
                        idempotency_key,
                        limitations,
                    ),
                )
                conn.execute(
                    """INSERT INTO audit_events
                    (actor_user_id,action,entity_type,entity_id,details)
                    VALUES (%s,'ZONING_REVIEW_REQUESTED','zoning_review',%s,%s)""",
                    (
                        actor_id,
                        review_id,
                        Jsonb(
                            {
                                "project_id": str(project_id),
                                "project_version_id": str(
                                    project["project_version_id"]
                                ),
                                "reason": "no_versioned_territorial_evidence",
                            }
                        ),
                    ),
                )
        return {
            "review_id": review_id,
            "project_id": project["project_id"],
            "project_version_id": project["project_version_id"],
            "status": "requires_review",
            "compatible": None,
            "location": project["location"],
            "proposed_land_use": project["proposed_land_use"],
            "territorial_data_origin": project["territorial_data_origin"],
            "evidence": [],
            "alerts": [
                "No se puede concluir compatibilidad sin evidencia territorial versionada."
            ],
            "limitations": limitations,
            "requires_human_review": True,
            "duplicated": False,
        }



    def search_normatives(
        self,
        query: str,
        actor_id: UUID,
        document_filter: str | None = None,
        only_in_force: bool = True,
        limit: int = 5,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Busca automaticamente fragmentos normativos versionados para el Asesor Juridico (HU2.1)."""
        cleaned_query = query.strip()
        if len(cleaned_query) < 2:
            raise ConfiguracionPMV1Error("La consulta debe tener al menos 2 caracteres")

        search_id = uuid4()
        try:
            if not _is_db_available(self.db_url):
                raise psycopg.OperationalError("Database unreachable")
            with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
                duplicated = False
                if idempotency_key and idempotency_key.strip():
                    prev = conn.execute(
                        "SELECT id, query FROM normative_search_logs WHERE idempotency_key = %s",
                        (idempotency_key.strip(),),
                    ).fetchone()
                    if prev:
                        if prev["query"].strip().lower() != cleaned_query.lower():
                            raise ConfiguracionPMV1Error(
                                "Idempotency-Key ya fue utilizada para otra consulta"
                            )
                        duplicated = True

                sql = (
                    "SELECT id, document_name, short_code, version, topic, content, "
                    "in_force, has_alert, data_origin FROM normative_documents WHERE 1=1"
                )
                params: list[Any] = []
                if only_in_force:
                    sql += " AND in_force = TRUE"
                if document_filter and document_filter.strip():
                    f = f"%{document_filter.strip()}%"
                    sql += " AND (document_name ILIKE %s OR short_code ILIKE %s)"
                    params.extend([f, f])

                rows = conn.execute(sql, tuple(params)).fetchall()

                keywords = NormativeSearchEngine.extract_keywords(cleaned_query)
                scored = []
                for r in rows:
                    item = dict(r)
                    score = NormativeSearchEngine.score_chunk(item, cleaned_query, keywords)
                    if score > 0:
                        item["relevance_score"] = score
                        item["location"] = NormativeSearchEngine.resolve_location(item)
                        scored.append(item)

                scored.sort(
                    key=lambda x: (x["relevance_score"], x["has_alert"]),
                    reverse=True,
                )
                results = scored[:limit]

                alerts_found = []
                for r in results:
                    if r.get("has_alert"):
                        alerts_found.append(
                            f"Alerta legal detectada en {r['id']} ({r['topic']}): {r['content']}"
                        )

                if not duplicated:
                    conn.execute(
                        """INSERT INTO normative_search_logs
                        (id, actor_user_id, query, document_filter, results_count, idempotency_key)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            search_id,
                            actor_id,
                            cleaned_query,
                            document_filter.strip() if document_filter else None,
                            len(results),
                            idempotency_key.strip() if idempotency_key else None,
                        ),
                    )
                    conn.execute(
                        """INSERT INTO audit_events
                        (actor_user_id, action, entity_type, entity_id, details)
                        VALUES (%s, 'NORMATIVE_SEARCH_PERFORMED', 'normative_search', %s, %s)""",
                        (
                            actor_id,
                            search_id,
                            Jsonb(
                                {
                                    "query": cleaned_query,
                                    "document_filter": document_filter.strip()
                                    if document_filter
                                    else None,
                                    "results_count": len(results),
                                    "alerts_count": len(alerts_found),
                                }
                            ),
                        ),
                    )
        except psycopg.OperationalError as err:
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de normativa no disponible: la base de datos no responde."
                ) from err
            fallback_rows = _load_fallback_seed_documents()
            if only_in_force:
                fallback_rows = [r for r in fallback_rows if r["in_force"]]
            if document_filter and document_filter.strip():
                df_lower = document_filter.strip().lower()
                fallback_rows = [
                    r for r in fallback_rows
                    if df_lower in r["document_name"].lower() or df_lower in r["short_code"].lower()
                ]

            keywords = NormativeSearchEngine.extract_keywords(cleaned_query)
            scored = []
            for item in fallback_rows:
                score = NormativeSearchEngine.score_chunk(item, cleaned_query, keywords)
                if score > 0:
                    item_copy = dict(item)
                    item_copy["relevance_score"] = score
                    item_copy["location"] = NormativeSearchEngine.resolve_location(item_copy)
                    scored.append(item_copy)

            scored.sort(
                key=lambda x: (x["relevance_score"], x["has_alert"]),
                reverse=True,
            )
            results = scored[:limit]

            alerts_found = []
            for r in results:
                if r.get("has_alert"):
                    alerts_found.append(
                        f"Alerta legal detectada en {r['id']} ({r['topic']}): {r['content']}"
                    )
            duplicated = False

        disclaimer = (
            "Material didactico y simulado para el PMV1 en El Tambo, Huancayo. "
            "La busqueda automatica asiste la consulta pero no emite dictamenes juridicos "
            "vinculantes ni sustituye el criterio del Asesor Juridico."
        )

        return {
            "query": cleaned_query,
            "document_filter": document_filter.strip() if document_filter else None,
            "total_results": len(results),
            "results": results,
            "alerts_found": alerts_found,
            "disclaimer": disclaimer,
            "requires_human_review": bool(alerts_found),
            "duplicated": duplicated,
        }

    def list_normative_documents(self) -> list[dict[str, Any]]:
        try:
            if not _is_db_available(self.db_url):
                raise psycopg.OperationalError("Database unreachable")
            with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
                rows = conn.execute(
                    """
                    SELECT short_code, document_name, version, in_force, data_origin,
                           COUNT(*)::int AS chunks_count
                    FROM normative_documents
                    GROUP BY short_code, document_name, version, in_force, data_origin
                    ORDER BY short_code
                    """
                ).fetchall()
            return [dict(r) for r in rows]
        except psycopg.OperationalError as err:
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de normativa no disponible: la base de datos no responde."
                ) from err
            docs = _load_fallback_seed_documents()
            grouped: dict[tuple[str, str, str, bool, str], int] = {}
            for d in docs:
                k = (d["short_code"], d["document_name"], d["version"], d["in_force"], d["data_origin"])
                grouped[k] = grouped.get(k, 0) + 1
            res = []
            for (code, name, ver, in_f, origin), count in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][2])):
                res.append({
                    "short_code": code,
                    "document_name": name,
                    "version": ver,
                    "in_force": in_f,
                    "data_origin": origin,
                    "chunks_count": count,
                })
            return res

    def submit_human_approval(
        self,
        project_id: UUID,
        actor_id: UUID,
        decision: str,
        justification: str,
        conditions: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Registra el dictamen humano formal sobre un proyecto tras la evaluacion tecnica."""
        cleaned_key = idempotency_key.strip()
        if not cleaned_key:
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")

        cleaned_decision = decision.strip().lower()
        if cleaned_decision not in ("approved", "rejected", "observed"):
            raise ConfiguracionPMV1Error("Dictamen invalido. Debe ser 'approved', 'rejected' u 'observed'")

        cleaned_justification = justification.strip()
        if len(cleaned_justification) < 5:
            raise ConfiguracionPMV1Error("La justificacion debe tener al menos 5 caracteres")

        cleaned_conditions = conditions.strip() if conditions and conditions.strip() else None
        if cleaned_decision == "observed" and not cleaned_conditions:
            raise ConfiguracionPMV1Error("El dictamen 'observed' requiere especificar condiciones u observaciones")

        project = self.get_project(project_id)
        if project["status"] not in ("evaluated", "approved", "rejected", "observed"):
            raise ConfiguracionPMV1Error(
                "El proyecto debe haber completado la evaluacion tecnica antes de la aprobacion humana formal"
            )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            prev = conn.execute(
                """
                SELECT id AS approval_id, project_id, project_version_id, decision,
                       justification, conditions, decided_by_user_id, idempotency_key, decided_at
                FROM human_approvals WHERE idempotency_key = %s
                """,
                (cleaned_key,),
            ).fetchone()
            if prev:
                if prev["project_id"] != project_id:
                    raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")
                return {**dict(prev), "duplicated": True}

            approval_id = uuid4()
            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO human_approvals
                (id, project_id, project_version_id, decision, justification,
                 conditions, decided_by_user_id, idempotency_key, decided_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    approval_id,
                    project_id,
                    project["project_version_id"],
                    cleaned_decision,
                    cleaned_justification,
                    cleaned_conditions,
                    actor_id,
                    cleaned_key,
                    now,
                ),
            )
            conn.execute(
                "UPDATE projects SET status = %s, updated_at = %s WHERE id = %s",
                (cleaned_decision, now, project_id),
            )
            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'PROJECT_HUMAN_APPROVAL_RECORDED', 'human_approval', %s, %s)
                """,
                (
                    actor_id,
                    approval_id,
                    Jsonb(
                        {
                            "project_id": str(project_id),
                            "project_version_id": str(project["project_version_id"]),
                            "decision": cleaned_decision,
                            "justification": cleaned_justification,
                            "conditions": cleaned_conditions,
                        }
                    ),
                ),
            )

        return {
            "approval_id": approval_id,
            "project_id": project_id,
            "project_version_id": project["project_version_id"],
            "decision": cleaned_decision,
            "justification": cleaned_justification,
            "conditions": cleaned_conditions,
            "decided_by_user_id": actor_id,
            "idempotency_key": cleaned_key,
            "decided_at": now,
            "duplicated": False,
        }

    def get_human_approval(self, project_id: UUID) -> dict[str, Any]:
        """Obtiene el estado de la compuerta humana y el ultimo dictamen del proyecto."""
        project = self.get_project(project_id)
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            latest = conn.execute(
                """
                SELECT id AS approval_id, project_id, project_version_id, decision,
                       justification, conditions, decided_by_user_id, idempotency_key, decided_at
                FROM human_approvals
                WHERE project_id = %s
                ORDER BY decided_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

        is_evaluated = project["status"] in ("evaluated", "approved", "rejected", "observed")
        requires_human_approval = project["status"] == "evaluated" and latest is None

        return {
            "project_id": project_id,
            "project_version_id": project["project_version_id"],
            "project_status": project["status"],
            "is_evaluated": is_evaluated,
            "requires_human_approval": requires_human_approval,
            "current_approval": dict(latest) if latest else None,
        }

    def evaluate_social_accessibility(
        self,
        project_id: UUID,
        actor_id: UUID,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Evalúa la accesibilidad territorial en salud, educación y transporte (HU1.4)."""
        project = self.get_project(project_id)
        cleaned_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None

        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de accesibilidad social no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            if cleaned_key:
                prev = conn.execute(
                    """
                    SELECT id, project_id, project_version_id, status, summary, results_json,
                           equity_json, social_score, score_explanation, evaluated_at, idempotency_key
                    FROM social_accessibility_assessments
                    WHERE idempotency_key = %s
                    """,
                    (cleaned_key,),
                ).fetchone()
                if prev:
                    if prev["project_id"] != project_id:
                        raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")
                    return {
                        "project_id": prev["project_id"],
                        "project_code": project["code"],
                        "project_version_id": prev["project_version_id"],
                        "status": prev["status"],
                        "summary": prev["summary"],
                        "categories": prev["results_json"]["categories"],
                        "equity": prev.get("equity_json") or prev["results_json"].get("equity"),
                        "social_score": float(prev["social_score"]) if prev.get("social_score") is not None else None,
                        "score_explanation": prev.get("score_explanation"),
                        "evaluated_at": prev["evaluated_at"],
                        "duplicated": True,
                    }

            rows = conn.execute(
                """
                SELECT id, project_id, project_code, category, indicator_name,
                       metric_value, metric_unit, has_sufficient_data, source_name,
                       data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM territorial_social_indicators
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            equity_rows = conn.execute(
                """
                SELECT id, project_id, project_code, dimension, has_sufficient_data,
                       target_group, aggregated_population, aggregated_percentage,
                       equity_criterion, declared_benefit, verifiable_data,
                       has_favorable_evidence, score_effect_pts, effect_type,
                       effect_explanation, source_name, data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM project_demographic_equity_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY dimension ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            assessment = SocialAccessibilityEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=project.get("project_version_id"),
                indicator_rows=[dict(r) for r in rows],
                equity_rows=[dict(r) for r in equity_rows],
            )

            assessment_id = uuid4()
            effective_key = cleaned_key or f"social-assessment-{assessment_id}"
            now = assessment["evaluated_at"]

            conn.execute(
                """
                INSERT INTO social_accessibility_assessments
                (id, project_id, project_version_id, requested_by_user_id, idempotency_key,
                 status, summary, results_json, equity_json, social_score, score_explanation, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assessment_id,
                    project_id,
                    project["project_version_id"],
                    actor_id,
                    effective_key,
                    assessment["status"],
                    assessment["summary"],
                    Jsonb({"categories": assessment["categories"], "equity": assessment.get("equity")}),
                    Jsonb(assessment["equity"]) if assessment.get("equity") else None,
                    assessment.get("social_score"),
                    assessment.get("score_explanation"),
                    now,
                ),
            )

            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'SOCIAL_ACCESSIBILITY_EVALUATED', 'social_assessment', %s, %s)
                """,
                (
                    actor_id,
                    assessment_id,
                    Jsonb(
                        {
                            "project_id": str(project_id),
                            "project_code": project["code"],
                            "status": assessment["status"],
                            "categories_count": len(assessment["categories"]),
                        }
                    ),
                ),
            )

        return {
            **assessment,
            "duplicated": False,
        }

    def get_social_accessibility(self, project_id: UUID) -> dict[str, Any]:
        """Obtiene la última evaluación de accesibilidad social o genera el análisis si aún no fue guardado."""
        project = self.get_project(project_id)

        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de accesibilidad social no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            latest = conn.execute(
                """
                SELECT id, project_id, project_version_id, status, summary, results_json,
                       equity_json, social_score, score_explanation, evaluated_at
                FROM social_accessibility_assessments
                WHERE project_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            if latest:
                return {
                    "project_id": latest["project_id"],
                    "project_code": project["code"],
                    "project_version_id": latest["project_version_id"],
                    "status": latest["status"],
                    "summary": latest["summary"],
                    "categories": latest["results_json"]["categories"],
                    "equity": latest.get("equity_json") or latest["results_json"].get("equity"),
                    "social_score": float(latest["social_score"]) if latest.get("social_score") is not None else None,
                    "score_explanation": latest.get("score_explanation"),
                    "evaluated_at": latest["evaluated_at"],
                    "duplicated": False,
                }

            rows = conn.execute(
                """
                SELECT id, project_id, project_code, category, indicator_name,
                       metric_value, metric_unit, has_sufficient_data, source_name,
                       data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM territorial_social_indicators
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            equity_rows = conn.execute(
                """
                SELECT id, project_id, project_code, dimension, has_sufficient_data,
                       target_group, aggregated_population, aggregated_percentage,
                       equity_criterion, declared_benefit, verifiable_data,
                       has_favorable_evidence, score_effect_pts, effect_type,
                       effect_explanation, source_name, data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM project_demographic_equity_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY dimension ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            assessment = SocialAccessibilityEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=project.get("project_version_id"),
                indicator_rows=[dict(r) for r in rows],
                equity_rows=[dict(r) for r in equity_rows],
            )
            return {
                **assessment,
                "duplicated": False,
            }

    def evaluate_environmental_assessment(
        self,
        project_id: UUID,
        actor_id: UUID,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Evalúa el impacto ambiental territorial del proyecto (HU1.6)."""
        project = self.get_project(project_id)
        cleaned_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None

        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de evaluación ambiental no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            if cleaned_key:
                prev = conn.execute(
                    """
                    SELECT id, project_id, project_version_id, status, risk_level,
                           risk_observation, requires_human_review, favorable, summary,
                           declared_vs_evidence_json, impacts_json, mitigations_json,
                           green_area_json, environmental_score, score_explanation,
                           evaluated_at, idempotency_key
                    FROM environmental_assessments
                    WHERE idempotency_key = %s
                    """,
                    (cleaned_key,),
                ).fetchone()
                if prev:
                    if prev["project_id"] != project_id:
                        raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")
                    return {
                        "project_id": prev["project_id"],
                        "project_code": project["code"],
                        "project_version_id": prev["project_version_id"],
                        "status": prev["status"],
                        "risk_level": prev["risk_level"],
                        "risk_level_label": {
                            "low": "Riesgo Bajo",
                            "moderate": "Riesgo Moderado",
                            "high": "Riesgo Alto",
                            "insufficient": "Información insuficiente",
                        }.get(prev["risk_level"], prev["risk_level"]),
                        "risk_observation": prev["risk_observation"],
                        "requires_human_review": prev["requires_human_review"],
                        "favorable": prev["favorable"],
                        "favorable_label": "Favorable condicionado a cumplimiento de mitigaciones" if prev["favorable"] is True else (
                            "No favorable - Requiere revisión técnica ambiental humana obligatoria" if prev["risk_level"] == "high" else (
                                "Desfavorable: puntaje ambiental insuficiente por afectación no mitigada de áreas verdes" if prev["favorable"] is False else
                                "Sin conclusión favorable: información insuficiente"
                            )
                        ),
                        "summary": prev["summary"],
                        "declared_vs_evidence": prev["declared_vs_evidence_json"],
                        "impacts": prev["impacts_json"],
                        "mitigations": prev["mitigations_json"],
                        "green_area": prev.get("green_area_json"),
                        "environmental_score": float(prev["environmental_score"]) if prev.get("environmental_score") is not None else None,
                        "score_explanation": prev.get("score_explanation"),
                        "evaluated_at": prev["evaluated_at"],
                        "duplicated": True,
                    }

            rows = conn.execute(
                """
                SELECT id, project_id, project_code, has_sufficient_data,
                       environmental_component, declared_impacts, declared_measures,
                       verifiable_evidence, proximity_to_water_meters,
                       is_in_protected_or_risk_area, source_name, data_origin, description
                FROM project_environmental_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            green_rows = conn.execute(
                """
                SELECT id, project_id, project_code, has_sufficient_data,
                       total_project_area_m2, green_area_m2, green_area_percentage,
                       delimitation_description, declared_affectation, verifiable_affectation,
                       affectation_type, protection_measures, has_sufficient_measures,
                       score_effect_pts, effect_type, calculation_explanation,
                       source_name, data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM project_green_area_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            assessment = EnvironmentalAssessmentEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=project.get("project_version_id"),
                records=[dict(r) for r in rows],
                green_records=[dict(g) for g in green_rows],
            )

            assessment_id = uuid4()
            effective_key = cleaned_key or f"env-assessment-{assessment_id}"
            now = assessment["evaluated_at"]

            conn.execute(
                """
                INSERT INTO environmental_assessments
                (id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
                 status, risk_level, risk_observation, requires_human_review, favorable,
                 summary, declared_vs_evidence_json, impacts_json, mitigations_json,
                 green_area_json, environmental_score, score_explanation, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assessment_id,
                    project_id,
                    project["project_version_id"],
                    actor_id,
                    effective_key,
                    assessment["status"],
                    assessment["risk_level"],
                    assessment["risk_observation"],
                    assessment["requires_human_review"],
                    assessment["favorable"],
                    assessment["summary"],
                    Jsonb(assessment["declared_vs_evidence"]),
                    Jsonb(assessment["impacts"]),
                    Jsonb(assessment["mitigations"]),
                    Jsonb(assessment["green_area"]) if assessment.get("green_area") else None,
                    assessment.get("environmental_score"),
                    assessment.get("score_explanation"),
                    now,
                ),
            )

            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'ENVIRONMENTAL_ASSESSMENT_EVALUATED', 'environmental_assessment', %s, %s)
                """,
                (
                    actor_id,
                    assessment_id,
                    Jsonb(
                        {
                            "project_id": str(project_id),
                            "project_code": project["code"],
                            "risk_level": assessment["risk_level"],
                            "requires_human_review": assessment["requires_human_review"],
                            "favorable": assessment["favorable"],
                        }
                    ),
                ),
            )

        return {
            **assessment,
            "duplicated": False,
        }

    def get_environmental_assessment(self, project_id: UUID) -> dict[str, Any]:
        """Obtiene la última evaluación ambiental o genera el análisis preliminar si aún no fue guardado."""
        project = self.get_project(project_id)

        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de evaluación ambiental no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            latest = conn.execute(
                """
                SELECT id, project_id, project_version_id, status, risk_level,
                       risk_observation, requires_human_review, favorable, summary,
                       declared_vs_evidence_json, impacts_json, mitigations_json,
                       green_area_json, environmental_score, score_explanation, evaluated_at
                FROM environmental_assessments
                WHERE project_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            if latest:
                return {
                    "project_id": latest["project_id"],
                    "project_code": project["code"],
                    "project_version_id": latest["project_version_id"],
                    "status": latest["status"],
                    "risk_level": latest["risk_level"],
                    "risk_level_label": {
                        "low": "Riesgo Bajo",
                        "moderate": "Riesgo Moderado",
                        "high": "Riesgo Alto",
                        "insufficient": "Información insuficiente",
                    }.get(latest["risk_level"], latest["risk_level"]),
                    "risk_observation": latest["risk_observation"],
                    "requires_human_review": latest["requires_human_review"],
                    "favorable": latest["favorable"],
                    "favorable_label": "Favorable condicionado a cumplimiento de mitigaciones" if latest["favorable"] is True else (
                        "No favorable - Requiere revisión técnica ambiental humana obligatoria" if latest["risk_level"] == "high" else (
                            "Desfavorable: puntaje ambiental insuficiente por afectación no mitigada de áreas verdes" if latest["favorable"] is False else
                            "Sin conclusión favorable: información insuficiente"
                        )
                    ),
                    "summary": latest["summary"],
                    "declared_vs_evidence": latest["declared_vs_evidence_json"],
                    "impacts": latest["impacts_json"],
                    "mitigations": latest["mitigations_json"],
                    "green_area": latest.get("green_area_json"),
                    "environmental_score": float(latest["environmental_score"]) if latest.get("environmental_score") is not None else None,
                    "score_explanation": latest.get("score_explanation"),
                    "evaluated_at": latest["evaluated_at"],
                    "duplicated": False,
                }

            rows = conn.execute(
                """
                SELECT id, project_id, project_code, has_sufficient_data,
                       environmental_component, declared_impacts, declared_measures,
                       verifiable_evidence, proximity_to_water_meters,
                       is_in_protected_or_risk_area, source_name, data_origin, description
                FROM project_environmental_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            green_rows = conn.execute(
                """
                SELECT id, project_id, project_code, has_sufficient_data,
                       total_project_area_m2, green_area_m2, green_area_percentage,
                       delimitation_description, declared_affectation, verifiable_affectation,
                       affectation_type, protection_measures, has_sufficient_measures,
                       score_effect_pts, effect_type, calculation_explanation,
                       source_name, data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM project_green_area_records
                WHERE project_id = %s OR project_code = %s
                ORDER BY created_at ASC
                """,
                (project_id, project["code"]),
            ).fetchall()

            assessment = EnvironmentalAssessmentEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=project.get("project_version_id"),
                records=[dict(r) for r in rows],
                green_records=[dict(g) for g in green_rows],
            )
            return {
                **assessment,
                "duplicated": False,
            }


class SocialAccessibilityEngine:
    """Motor de evaluación social territorial: accesibilidad (HU1.4) y equidad demográfica (HU1.5).

    Garantiza el cumplimiento estricto de los criterios de aceptación:
    - CA-HU1.4-01 / CA-HU1.4-02: Presenta por separado salud, educación y transporte.
    - CA-HU1.5-01: Muestra cómo los indicadores agregados de género y edad influyen en el resultado social.
    - CA-HU1.5-02: Cuando falten datos fiables, señala la limitación, no infiere proporciones y no asigna
      resultado favorable sin evidencia (efecto no determinado / None, nunca 0.0 pts ni ventaja automática).
    """

    CANONICAL_CATEGORIES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("salud", "Accesibilidad a Salud"),
        ("educacion", "Accesibilidad a Educación"),
        ("transporte", "Accesibilidad a Transporte"),
    )

    @classmethod
    def build_category_item(
        cls,
        category: str,
        category_label: str,
        indicator_row: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not indicator_row or not indicator_row.get("has_sufficient_data") or indicator_row.get("metric_value") is None:
            source = indicator_row.get("source_name") if indicator_row else "Registro Catastral Municipal El Tambo (Sin cobertura)"
            data_origin = indicator_row.get("data_origin") if indicator_row else "simulated"
            is_sim = indicator_row.get("is_simulated", True) if indicator_row else True
            return {
                "category": category,
                "category_label": category_label,
                "status": "insufficient",
                "has_sufficient_data": False,
                "indicator": indicator_row.get("indicator_name") if indicator_row else f"Indicador territorial de {category}",
                "value": None,
                "unit": None,
                "source": source,
                "data_origin": data_origin,
                "is_simulated": is_sim,
                "message": "Información insuficiente",
            }

        val = float(indicator_row["metric_value"])
        unit = indicator_row["metric_unit"]
        ind_name = indicator_row["indicator_name"]
        source = indicator_row["source_name"]
        data_origin = indicator_row["data_origin"]
        is_sim = indicator_row.get("is_simulated", True)
        desc = indicator_row.get("description") or f"{ind_name}: {val} {unit}"

        return {
            "category": category,
            "category_label": category_label,
            "status": "sufficient",
            "has_sufficient_data": True,
            "indicator": ind_name,
            "value": val,
            "unit": unit,
            "source": source,
            "data_origin": data_origin,
            "is_simulated": is_sim,
            "message": desc,
        }

    @classmethod
    def _evaluate_dimension(
        cls,
        dim_key: Literal["genero", "edad"],
        dim_label: str,
        row: dict[str, Any] | None,
    ) -> dict[str, Any]:
        default_target = "Mujeres y niñas del área de influencia" if dim_key == "genero" else "Niñez (<12) y adultos mayores (≥65)"
        default_criterion = (
            "Priorización de equipamiento seguro y reducción de brechas con enfoque de género"
            if dim_key == "genero"
            else "Acceso universal y equipamiento adaptado para niñez y personas adultas mayores"
        )
        default_source = "Catastro Municipal El Tambo (Sin cobertura demográfica desagregada)"

        if not row or not row.get("has_sufficient_data") or row.get("aggregated_percentage") is None:
            return {
                "dimension": dim_key,
                "dimension_label": dim_label,
                "target_group": row.get("target_group") if row else default_target,
                "has_sufficient_data": False,
                "aggregated_population": None,
                "aggregated_percentage": None,
                "equity_criterion": row.get("equity_criterion") if row else default_criterion,
                "declared_benefit": row.get("declared_benefit") if row else None,
                "verifiable_data": None,
                "has_favorable_evidence": False,
                "score_effect_pts": None,
                "effect_type": "indeterminado",
                "effect_explanation": (
                    f"Información insuficiente: no se dispone de datos demográficos fiables para {dim_label.lower()}. "
                    "Conforme a la regla de precaución (CA-HU1.5-02), no se infieren proporciones ni se otorga bonificación sin evidencia."
                ),
                "source_name": row.get("source_name") if row else default_source,
                "data_origin": row.get("data_origin", "simulated") if row else "simulated",
                "is_simulated": True,
            }

        pop = int(row["aggregated_population"]) if row.get("aggregated_population") is not None else None
        pct = float(row["aggregated_percentage"])
        pts = float(row["score_effect_pts"]) if row.get("score_effect_pts") is not None else 0.0
        effect_t = str(row.get("effect_type", "neutro"))
        fav_ev = bool(row.get("has_favorable_evidence", False))
        expl = row.get("effect_explanation") or f"Efecto {effect_t} ({pts:+.1f} pts) en {dim_label.lower()}."

        return {
            "dimension": dim_key,
            "dimension_label": dim_label,
            "target_group": row.get("target_group") or default_target,
            "has_sufficient_data": True,
            "aggregated_population": pop,
            "aggregated_percentage": pct,
            "equity_criterion": row.get("equity_criterion") or default_criterion,
            "declared_benefit": row.get("declared_benefit"),
            "verifiable_data": row.get("verifiable_data"),
            "has_favorable_evidence": fav_ev,
            "score_effect_pts": pts,
            "effect_type": effect_t,
            "effect_explanation": expl,
            "source_name": row.get("source_name") or default_source,
            "data_origin": row.get("data_origin", "simulated"),
            "is_simulated": row.get("data_origin", "simulated") == "simulated",
        }

    @classmethod
    def _evaluate_demographic_equity(
        cls,
        equity_rows: list[dict[str, Any]] | None,
        base_score: float | None,
    ) -> tuple[dict[str, Any], float | None, str]:
        rows_by_dim = {str(r["dimension"]).lower(): r for r in (equity_rows or [])}
        gender_item = cls._evaluate_dimension("genero", "Equidad de Género", rows_by_dim.get("genero"))
        age_item = cls._evaluate_dimension("edad", "Equidad de Edad", rows_by_dim.get("edad"))

        has_sufficient_data = gender_item["has_sufficient_data"] and age_item["has_sufficient_data"]
        any_sufficient = gender_item["has_sufficient_data"] or age_item["has_sufficient_data"]

        if has_sufficient_data:
            g_pts = gender_item["score_effect_pts"] or 0.0
            a_pts = age_item["score_effect_pts"] or 0.0
            equity_pts = g_pts + a_pts
            summary_eq = (
                f"Evaluación de equidad completa: género ({gender_item['effect_type']}, {g_pts:+.1f} pts) "
                f"y edad ({age_item['effect_type']}, {a_pts:+.1f} pts)."
            )
        elif any_sufficient:
            equity_pts = None
            dim_ok = "género" if gender_item["has_sufficient_data"] else "edad"
            dim_missing = "edad" if not age_item["has_sufficient_data"] else "género"
            summary_eq = (
                f"Evaluación de equidad parcial: datos suficientes en {dim_ok}, pero información insuficiente en {dim_missing}. "
                "No se infieren proporciones ni ventaja automática para el grupo faltante (CA-HU1.5-02)."
            )
        else:
            equity_pts = None
            summary_eq = (
                "Información insuficiente en género y edad: no se dispone de datos demográficos fiables. "
                "Conforme a CA-HU1.5-02, no se infieren proporciones ni se otorga bonificación automática sin evidencia."
            )

        equity_dict = {
            "has_sufficient_data": has_sufficient_data,
            "gender": gender_item,
            "age": age_item,
            "equity_score_pts": equity_pts,
            "effect_summary": summary_eq,
        }

        if base_score is None or not any_sufficient:
            final_social_score = None
            score_expl = (
                "Puntaje social no determinado: información insuficiente en accesibilidad territorial o datos demográficos "
                "de equidad para ponderación cuantitativa (CA-HU1.4-02 / CA-HU1.5-02)."
            )
        else:
            g_pts = gender_item["score_effect_pts"] if gender_item["score_effect_pts"] is not None else 0.0
            a_pts = age_item["score_effect_pts"] if age_item["score_effect_pts"] is not None else 0.0
            final_social_score = min(100.0, max(0.0, base_score + g_pts + a_pts))

            g_desc = f"{gender_item['score_effect_pts']:+.1f} pts" if gender_item["score_effect_pts"] is not None else "No determinado"
            a_desc = f"{age_item['score_effect_pts']:+.1f} pts" if age_item["score_effect_pts"] is not None else "No determinado"

            score_expl = (
                f"Puntaje social preliminar: {final_social_score:.1f}/100 pts "
                f"(Base accesibilidad: {base_score:.1f} pts, Género: {g_desc}, Edad: {a_desc}). "
                "Regla de demostración para el prototipo PMV2 (HU1.5)."
            )

        return equity_dict, final_social_score, score_expl

    @classmethod
    def evaluate(
        cls,
        project_id: UUID,
        project_code: str,
        project_version_id: UUID | None,
        indicator_rows: list[dict[str, Any]],
        equity_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        rows_by_category = {str(r["category"]).lower(): r for r in indicator_rows}
        categories_output: list[dict[str, Any]] = []

        insufficient_count = 0
        for cat_key, cat_label in cls.CANONICAL_CATEGORIES:
            row = rows_by_category.get(cat_key)
            item = cls.build_category_item(cat_key, cat_label, row)
            if not item["has_sufficient_data"]:
                insufficient_count += 1
            categories_output.append(item)

        if insufficient_count == 0:
            base_score = 70.0
            cat_summary = "Análisis de accesibilidad social completo (salud, educación y transporte)."
        elif insufficient_count == len(cls.CANONICAL_CATEGORIES):
            base_score = None
            cat_summary = "Información insuficiente: no se dispone de datos de cobertura para salud, educación o transporte."
        else:
            base_score = 50.0
            cat_summary = (
                f"Análisis de accesibilidad social parcial: {len(cls.CANONICAL_CATEGORIES) - insufficient_count} "
                f"categoría(s) con datos suficientes y {insufficient_count} con Información insuficiente."
            )

        if equity_rows is not None:
            equity_dict, social_score, score_expl = cls._evaluate_demographic_equity(
                equity_rows=equity_rows,
                base_score=base_score,
            )
            # Estado global integrado con equidad
            if insufficient_count == 0 and equity_dict["has_sufficient_data"]:
                status = "complete"
                summary = f"{cat_summary} Se integraron indicadores demográficos de género y edad con criterios de equidad."
            elif insufficient_count == len(cls.CANONICAL_CATEGORIES) and not equity_dict["has_sufficient_data"]:
                status = "insufficient"
                summary = "Información insuficiente en accesibilidad y equidad social: no se emite resultado favorable por defecto."
            else:
                status = "partial"
                summary = f"{cat_summary} {equity_dict['effect_summary']}"
        else:
            equity_dict = None
            social_score = base_score
            score_expl = (
                f"Puntaje Base de Accesibilidad Territorial: {base_score:.1f} pts."
                if base_score is not None
                else "Información insuficiente de accesibilidad."
            )
            if insufficient_count == 0:
                status = "complete"
                summary = cat_summary
            elif insufficient_count == len(cls.CANONICAL_CATEGORIES):
                status = "insufficient"
                summary = cat_summary
            else:
                status = "partial"
                summary = cat_summary

        return {
            "project_id": project_id,
            "project_code": project_code,
            "project_version_id": project_version_id,
            "status": status,
            "summary": summary,
            "categories": categories_output,
            "equity": equity_dict,
            "social_score": social_score,
            "score_explanation": score_expl,
            "evaluated_at": datetime.now(timezone.utc),
        }


class EnvironmentalAssessmentEngine:
    """Motor de evaluación de impacto ambiental territorial (HU1.6).

    Cumple estrictamente los criterios de aceptación:
    - CA-HU1.6-01: Muestra impactos identificados, nivel de riesgo estimado, sustento y
      posibles mitigaciones, diferenciando lo declarado en el expediente de la evidencia verificable.
    - CA-HU1.6-02: Ante posible impacto alto, registra una observación de riesgo que requiere
      consideración humana obligatoria antes de cualquier decisión favorable (prohibiendo aprobación automática).
    - CA-HU1.6-03: Si faltan datos ambientales esenciales, muestra 'Información insuficiente'
      y nunca una conclusión favorable por defecto (favorable=None/False).
    """

    @classmethod
    def _evaluate_green_area(
        cls,
        green_records: list[dict[str, Any]] | None,
        base_score: float | None,
        is_high_risk: bool,
    ) -> tuple[dict[str, Any], float | None, str]:
        g_rec = green_records[0] if green_records else None
        if not g_rec or not g_rec.get("has_sufficient_data"):
            green_dict = {
                "has_sufficient_data": False,
                "total_project_area_m2": None,
                "green_area_m2": None,
                "green_area_percentage": None,
                "delimitation_description": None,
                "declared_affectation": None,
                "verifiable_affectation": None,
                "affectation_type": None,
                "affectation_type_label": "No determinada: información insuficiente",
                "protection_measures": None,
                "has_sufficient_measures": False,
                "score_effect_pts": None,
                "effect_type": "indeterminado",
                "calculation_explanation": (
                    "Información insuficiente: no se dispone de superficie, delimitación o sustento suficiente de áreas verdes. "
                    "Conforme a la regla de precaución (CA-HU1.7-02), no se concede ventaja ambiental ni bonificación automática."
                ),
                "source_name": g_rec.get("source_name") if g_rec else "Catastro Municipal El Tambo (Sin catastro verde ni delimitación)",
                "data_origin": "simulated",
                "is_simulated": True,
            }
            return (
                green_dict,
                None,
                "Puntaje ambiental no determinado: información de áreas verdes insuficiente para ponderación cuantitativa (CA-HU1.7-02)."
            )

        total_area = float(g_rec.get("total_project_area_m2") or 0.0)
        green_m2 = float(g_rec.get("green_area_m2") or 0.0)
        green_pct = float(g_rec.get("green_area_percentage") or ((green_m2 / total_area * 100.0) if total_area > 0 else 0.0))
        delimitation = g_rec.get("delimitation_description") or "Delimitación perimétrica no especificada"
        declared_aff = g_rec.get("declared_affectation") or "No declarada"
        verifiable_aff = g_rec.get("verifiable_affectation") or "Sin hallazgos cartográficos"
        aff_type = g_rec.get("affectation_type") or "indeterminada"
        measures = g_rec.get("protection_measures") or "No especificadas"
        suff_measures = bool(g_rec.get("has_sufficient_measures", True))

        aff_labels = {
            "conservacion_positiva": "Conservación activa / Aumento de área verde",
            "afectacion_no_mitigada": "Afectación negativa sin mitigación suficiente",
            "afectacion_mitigada": "Intervención con medidas de mitigación",
            "sin_afectacion": "Sin afectación a cobertura vegetal",
            "indeterminada": "Afectación no determinada",
        }
        aff_label = aff_labels.get(aff_type, aff_type)

        if base_score is None:
            score_effect_pts = None
            effect_type = "indeterminado"
            calc_expl = "Información ambiental base insuficiente: no es posible computar puntaje consolidado."
            explanation = calc_expl
            final_score = None
        else:
            if aff_type in ("conservacion_positiva", "sin_afectacion") and suff_measures:
                score_effect_pts = 15.0
                effect_type = "bonus"
                calc_expl = (
                    f"Bonificación ambiental (+15.0 pts): el proyecto conserva y protege {green_m2:.2f} m² "
                    f"({green_pct:.1f}% del predio) de áreas verdes con delimitación verificada y medidas de protección suficientes."
                )
            elif aff_type == "afectacion_no_mitigada" or (aff_type == "afectacion_mitigada" and not suff_measures):
                score_effect_pts = -20.0
                effect_type = "penalizacion"
                calc_expl = (
                    f"Deducción ambiental (-20.0 pts): el proyecto genera afectación/reducción de {green_m2:.2f} m² "
                    f"de área verde sin medidas de compensación suficientes ({measures})."
                )
            else:
                score_effect_pts = 0.0
                effect_type = "neutro"
                calc_expl = (
                    f"Efecto neutro (0.0 pts): la intervención sobre {green_m2:.2f} m² de área verde "
                    "cuenta con medidas de reposición y compensación equivalentes acreditadas."
                )

            final_score = max(0.0, min(100.0, base_score + score_effect_pts))
            if is_high_risk:
                explanation = (
                    f"Puntaje ambiental preliminar: {final_score:.1f}/100 pts (Base de riesgo alto: {base_score:.1f} pts, {calc_expl}). "
                    "ALERTA DE RIESGO PREVALENTE: La valoración de áreas verdes no convalida ni convierte en favorable el expediente "
                    "ante la presencia de RIESGO AMBIENTAL ALTO (faja marginal fluvial intangible). "
                    "La aprobación automática queda prohibida (CA-HU1.6-02 / CA-HU1.7-01)."
                )
            else:
                explanation = (
                    f"Puntaje ambiental preliminar: {final_score:.1f}/100 pts (Base ambiental: {base_score:.1f} pts, {calc_expl}). "
                    "Regla de demostración para el prototipo PMV2 (HU1.7)."
                )

        green_dict = {
            "has_sufficient_data": True,
            "total_project_area_m2": total_area,
            "green_area_m2": green_m2,
            "green_area_percentage": green_pct,
            "delimitation_description": delimitation,
            "declared_affectation": declared_aff,
            "verifiable_affectation": verifiable_aff,
            "affectation_type": aff_type,
            "affectation_type_label": aff_label,
            "protection_measures": measures,
            "has_sufficient_measures": suff_measures,
            "score_effect_pts": score_effect_pts,
            "effect_type": effect_type,
            "calculation_explanation": calc_expl,
            "source_name": g_rec.get("source_name") or "Dataset territorial simulado SIPRIM El Tambo - Gerencia de Gestión Ambiental MPH (Simulado)",
            "data_origin": g_rec.get("data_origin", "simulated"),
            "is_simulated": g_rec.get("data_origin", "simulated") == "simulated",
        }
        return green_dict, final_score, explanation

    @classmethod
    def evaluate(
        cls,
        project_id: UUID,
        project_code: str,
        project_version_id: UUID | None,
        records: list[dict[str, Any]],
        green_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        if not records or any(not r.get("has_sufficient_data") for r in records):
            rec = records[0] if records else None
            declared_vs_evidence = {
                "declared_by_applicant": rec.get("declared_impacts") if rec else None,
                "declared_measures": rec.get("declared_measures") if rec else None,
                "verifiable_evidence": None,
                "evidence_source": rec.get("source_name") if rec else "Catastro Municipal El Tambo (Sin cobertura)",
                "is_simulated": True,
                "proximity_to_water_meters": None,
                "is_in_protected_or_risk_area": None,
            }
            green_item, env_score, score_expl = cls._evaluate_green_area(
                green_records=green_records,
                base_score=None,
                is_high_risk=False,
            )
            return {
                "project_id": project_id,
                "project_code": project_code,
                "project_version_id": project_version_id,
                "status": "insufficient",
                "risk_level": "insufficient",
                "risk_level_label": "Información insuficiente",
                "risk_observation": None,
                "requires_human_review": False,
                "favorable": None,
                "favorable_label": "Sin conclusión favorable: información insuficiente",
                "summary": "Información insuficiente: el expediente no cuenta con datos ambientales esenciales, Declaración de Impacto Ambiental (DIA) ni línea base territorial de demostración disponible.",
                "declared_vs_evidence": declared_vs_evidence,
                "impacts": [],
                "mitigations": [],
                "green_area": green_item,
                "environmental_score": env_score,
                "score_explanation": score_expl,
                "evaluated_at": now,
            }

        is_high_risk = False
        high_risk_reasons = []
        impacts: list[dict[str, Any]] = []
        mitigations: list[dict[str, Any]] = []

        all_declared_impacts = []
        all_declared_measures = []
        all_verifiable_evidence = []
        sources = set()
        min_water_dist: float | None = None
        in_protected_area = False

        for r in records:
            if r.get("declared_impacts"):
                all_declared_impacts.append(r["declared_impacts"])
            if r.get("declared_measures"):
                all_declared_measures.append(r["declared_measures"])
            if r.get("verifiable_evidence"):
                all_verifiable_evidence.append(r["verifiable_evidence"])
            if r.get("source_name"):
                sources.add(r["source_name"])

            prox = r.get("proximity_to_water_meters")
            if prox is not None:
                prox_val = float(prox)
                if min_water_dist is None or prox_val < min_water_dist:
                    min_water_dist = prox_val
                if prox_val < 50.0:
                    is_high_risk = True
                    high_risk_reasons.append(f"Distancia crítica a cuerpo de agua o faja marginal ({prox_val:.1f} m < 50 m reglamentarios).")

            if r.get("is_in_protected_or_risk_area"):
                in_protected_area = True
                is_high_risk = True
                high_risk_reasons.append("Ubicación en zona de riesgo alto/no mitigable o faja marginal intangible según PDM Huancayo / CENEPRED.")

            comp = r.get("environmental_component", "integral")
            if "hidrico" in comp or in_protected_area:
                impacts.append({
                    "component": "recurso_hidrico",
                    "component_label": "Recurso Hídrico y Faja Marginal",
                    "description": "Riesgo de contaminación por vertimientos, escorrentía con contaminantes y alteración del régimen fluvial.",
                    "severity": "alta" if is_high_risk else "moderada",
                    "substantiation": r.get("verifiable_evidence") or "Proximidad a cauce o faja marginal fluvial.",
                    "mitigations": [
                        "Reubicación fuera de la faja marginal intangible según PDM Huancayo",
                        "Instalación de trampas de grasa y desarenadores certificados",
                        "Plan de contingencia obligatorio ante crecidas fluviales"
                    ]
                })
                mitigations.append({
                    "component": "recurso_hidrico",
                    "measure": "Delimitación estricta y retiro obligatorio del cauce fluvial según plano PDM Huancayo.",
                    "type": "preventiva",
                    "origin": "requerimiento_tecnico"
                })
            else:
                impacts.append({
                    "component": "aire_acustico",
                    "component_label": "Emisiones Atmosféricas y Ruido",
                    "description": "Generación temporal de polvo y niveles sonoros diurnos durante obras civiles preliminares.",
                    "severity": "moderada",
                    "substantiation": r.get("verifiable_evidence") or "Obra en zona urbana consolidada.",
                    "mitigations": [
                        "Aspersión periódica de agua para control de polvo",
                        "Cerco perimétrico con malla antipolvo",
                        "Horario de trabajo diurno controlado (08:00 - 17:00 h)"
                    ]
                })
                impacts.append({
                    "component": "suelo_residuos",
                    "component_label": "Gestión de Residuos de Demolición",
                    "description": "Generación de escombros y material excedente de obra civil.",
                    "severity": "baja",
                    "substantiation": "Residuos inertes de concreto y afirmado.",
                    "mitigations": [
                        "Transporte cubierto hacia escombrera autorizada municipal",
                        "Segregación en obra de materiales reutilizables"
                    ]
                })
                mitigations.append({
                    "component": "aire_acustico",
                    "measure": "Aspersión diaria y cerco perimétrico con malla antipolvo.",
                    "type": "preventiva",
                    "origin": "propuesta_expediente"
                })
                mitigations.append({
                    "component": "suelo_residuos",
                    "measure": "Disposición final exclusiva en escombrera autorizada por la Municipalidad de El Tambo.",
                    "type": "correctiva",
                    "origin": "requerimiento_tecnico"
                })

        source_str = " | ".join(sorted(sources)) if sources else "Dataset ambiental simulado SIPRIM El Tambo (Simulado)"
        declared_vs_evidence = {
            "declared_by_applicant": " // ".join(all_declared_impacts) if all_declared_impacts else None,
            "declared_measures": " // ".join(all_declared_measures) if all_declared_measures else None,
            "verifiable_evidence": " // ".join(all_verifiable_evidence) if all_verifiable_evidence else None,
            "evidence_source": source_str,
            "is_simulated": True,
            "proximity_to_water_meters": min_water_dist,
            "is_in_protected_or_risk_area": in_protected_area,
        }

        if is_high_risk:
            risk_observation = (
                "OBSERVACIÓN DE RIESGO AMBIENTAL ALTO: " + " ".join(high_risk_reasons) +
                " Se prohíbe la aprobación automática. Requiere consideración técnica ambiental humana obligatoria antes de cualquier decisión favorable."
            )
            green_item, env_score, score_expl = cls._evaluate_green_area(
                green_records=green_records,
                base_score=25.0,
                is_high_risk=True,
            )
            return {
                "project_id": project_id,
                "project_code": project_code,
                "project_version_id": project_version_id,
                "status": "sufficient",
                "risk_level": "high",
                "risk_level_label": "Riesgo Alto",
                "risk_observation": risk_observation,
                "requires_human_review": True,
                "favorable": None,
                "favorable_label": "No favorable - Requiere revisión técnica ambiental humana obligatoria",
                "summary": "Alerta ambiental: se identificó un nivel de riesgo ambiental ALTO. El expediente requiere pronunciamiento técnico humano formal antes de una decisión favorable.",
                "declared_vs_evidence": declared_vs_evidence,
                "impacts": impacts,
                "mitigations": mitigations,
                "green_area": green_item,
                "environmental_score": env_score,
                "score_explanation": score_expl,
                "evaluated_at": now,
            }

        green_item, env_score, score_expl = cls._evaluate_green_area(
            green_records=green_records,
            base_score=70.0,
            is_high_risk=False,
        )
        is_favorable = True
        fav_label = "Favorable condicionado a cumplimiento de mitigaciones"
        summary_text = "Evaluación ambiental con riesgo MODERADO: impactos de obra mitigables mediante las medidas ambientales programadas."
        if env_score is not None and env_score < 60.0:
            is_favorable = False
            fav_label = "Desfavorable: puntaje ambiental insuficiente por afectación no mitigada de áreas verdes"
            summary_text = (
                f"Evaluación ambiental DESFAVORABLE: puntaje de {env_score:.1f}/100 pts inferior al umbral aprobatorio (60.0 pts) "
                "debido a la afectación no mitigada de áreas verdes."
            )

        return {
            "project_id": project_id,
            "project_code": project_code,
            "project_version_id": project_version_id,
            "status": "sufficient",
            "risk_level": "moderate",
            "risk_level_label": "Riesgo Moderado",
            "risk_observation": None,
            "requires_human_review": False,
            "favorable": is_favorable,
            "favorable_label": fav_label,
            "summary": summary_text,
            "declared_vs_evidence": declared_vs_evidence,
            "impacts": impacts,
            "mitigations": mitigations,
            "green_area": green_item,
            "environmental_score": env_score,
            "score_explanation": score_expl,
            "evaluated_at": now,
        }


class EconomicProcessor:
    """Consumidor propietario exclusivo de economic_db e idempotente por event_id."""

    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    @staticmethod
    def calculate(
        budget: Decimal,
        beneficiaries: int,
        excellent: Decimal,
        unacceptable: Decimal,
    ) -> tuple[Decimal, Decimal]:
        if budget <= 0 or beneficiaries <= 0 or not 0 < excellent < unacceptable:
            raise ValueError("Datos economicos o umbrales invalidos")
        exact_cost = budget / Decimal(beneficiaries)
        if exact_cost <= excellent:
            score = Decimal(100)
        elif exact_cost >= unacceptable:
            score = Decimal(0)
        else:
            score = (
                Decimal(100) * (unacceptable - exact_cost) / (unacceptable - excellent)
            )
        return (
            exact_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = UUID(payload["event_id"])
        evaluation_id = UUID(payload["evaluation_id"])
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
                existing = conn.execute(
                    """SELECT ea.* FROM processed_requests pr
                    JOIN economic_assessments ea ON ea.id=pr.assessment_id
                    WHERE pr.event_id=%s OR pr.evaluation_id=%s""",
                    (event_id, evaluation_id),
                ).fetchone()
                if existing:
                    return self._completion(event_id, existing)

                budget = Decimal(payload["budget_pen"])
                beneficiaries = int(payload["beneficiaries_count"])
                excellent = Decimal(payload["excellent_cost_pen"])
                unacceptable = Decimal(payload["unacceptable_cost_pen"])
                cost, score = self.calculate(
                    budget, beneficiaries, excellent, unacceptable
                )
                assessment_id = uuid4()
                explanation = (
                    f"Costo por beneficiario = S/ {budget} / {beneficiaries} = S/ {cost}. "
                    f"Umbrales: excelente S/ {excellent}, inaceptable S/ {unacceptable}; score {score}/100. "
                    "No representa retorno socioeconomico ni viabilidad oficial."
                )
                row = {
                    "id": assessment_id,
                    "evaluation_id": evaluation_id,
                    "cost_per_beneficiary_pen": cost,
                    "score_0_100": score,
                    "explanation": explanation,
                    "algorithm_version": "economic-cost-per-beneficiary-v1",
                }
                conn.execute(
                    """INSERT INTO economic_assessments
                    (id,evaluation_id,project_version_id,criteria_version_id,budget_snapshot_pen,
                     beneficiaries_snapshot,excellent_cost_snapshot_pen,unacceptable_cost_snapshot_pen,
                     cost_per_beneficiary_pen,score_0_100,explanation,algorithm_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        assessment_id,
                        evaluation_id,
                        UUID(payload["project_version_id"]),
                        UUID(payload["criteria_version_id"]),
                        budget,
                        beneficiaries,
                        excellent,
                        unacceptable,
                        cost,
                        score,
                        explanation,
                        row["algorithm_version"],
                    ),
                )
                conn.execute(
                    """INSERT INTO assessment_metrics (id,assessment_id,metric_code,numeric_value,unit,formula)
                    VALUES (%s,%s,'COST_PER_BENEFICIARY',%s,'PEN/person','budget / beneficiaries'),
                           (%s,%s,'ECONOMIC_SCORE',%s,'points','linear normalization between thresholds')""",
                    (uuid4(), assessment_id, cost, uuid4(), assessment_id, score),
                )
                conn.execute(
                    "INSERT INTO processed_requests (event_id,evaluation_id,assessment_id) VALUES (%s,%s,%s)",
                    (event_id, evaluation_id, assessment_id),
                )
        return self._completion(event_id, row)

    @staticmethod
    def _completion(request_event_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
        return {
            # Estable para que un reintento no genere un segundo evento lógico.
            "event_id": str(
                uuid5(
                    NAMESPACE_URL, f"siprim:economic-completed:{row['evaluation_id']}"
                )
            ),
            "request_event_id": str(request_event_id),
            "event_type": "EconomicEvaluationCompleted",
            "evaluation_id": str(row["evaluation_id"]),
            "economic_assessment_id": str(row["id"]),
            "cost_per_beneficiary_pen": str(row["cost_per_beneficiary_pen"]),
            "score_0_100": str(row["score_0_100"]),
            "explanation": row["explanation"],
            "algorithm_version": row["algorithm_version"],
            "schema_version": 1,
        }


class CompletionProcessor:
    """Proyecta el evento en platform_db, con inbox para tolerar reintentos."""

    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    def process(self, payload: dict[str, Any]) -> None:
        event_id, evaluation_id = (
            UUID(payload["event_id"]),
            UUID(payload["evaluation_id"]),
        )
        with psycopg.connect(self.db_url) as conn:
            with conn.transaction():
                inserted = conn.execute(
                    "INSERT INTO inbox_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING event_id",
                    (event_id,),
                ).fetchone()
                if not inserted:
                    return
                conn.execute(
                    """INSERT INTO economic_result_projections
                    (evaluation_id,economic_assessment_id,cost_per_beneficiary_pen,score_0_100,
                     explanation,algorithm_version) VALUES (%s,%s,%s,%s,%s,%s)""",
                    (
                        evaluation_id,
                        UUID(payload["economic_assessment_id"]),
                        Decimal(payload["cost_per_beneficiary_pen"]),
                        Decimal(payload["score_0_100"]),
                        payload["explanation"],
                        payload["algorithm_version"],
                    ),
                )
                conn.execute(
                    "UPDATE evaluations SET status='completed',finished_at=now() WHERE id=%s",
                    (evaluation_id,),
                )
                conn.execute(
                    """UPDATE projects SET status='evaluated',updated_at=now()
                    WHERE id=(SELECT pv.project_id FROM project_versions pv JOIN evaluations e
                              ON e.project_version_id=pv.id WHERE e.id=%s)""",
                    (evaluation_id,),
                )
                conn.execute(
                    """INSERT INTO audit_events (action,entity_type,entity_id,details)
                    VALUES ('EVALUATION_COMPLETED','evaluation',%s,%s)""",
                    (
                        evaluation_id,
                        Jsonb(
                            {
                                "event_id": str(event_id),
                                "assessment_id": payload["economic_assessment_id"],
                            }
                        ),
                    ),
                )


class EvaluationStartedProcessor:
    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    def process(self, evaluation_id: str) -> None:
        with psycopg.connect(self.db_url) as conn:
            conn.execute(
                """UPDATE evaluations SET status='processing', started_at=COALESCE(started_at,now())
                WHERE id=%s AND status='queued'""",
                (UUID(evaluation_id),),
            )


class OutboxPublisher:
    """Recupera publicaciones que fallaron tras confirmar la transaccion local."""

    def __init__(self, db_url: str, dispatcher: TaskDispatcher) -> None:
        self.db_url = _dsn(db_url)
        self.dispatcher = dispatcher

    def publish_pending(self, limit: int = 50) -> int:
        published = 0
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                """SELECT id,payload FROM outbox_events WHERE published_at IS NULL
                ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s""",
                (limit,),
            ).fetchall()
            for row in rows:
                try:
                    self.dispatcher.dispatch_economic(row["payload"])
                    conn.execute(
                        "UPDATE outbox_events SET published_at=now(),publish_attempts=publish_attempts+1 WHERE id=%s",
                        (row["id"],),
                    )
                    published += 1
                except Exception:
                    conn.execute(
                        "UPDATE outbox_events SET publish_attempts=publish_attempts+1 WHERE id=%s",
                        (row["id"],),
                    )
        return published
