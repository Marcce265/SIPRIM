from __future__ import annotations

import os
import socket
import hashlib
import math
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

from backend.application.dto.pmv1_dto import PMV1ProjectCreate, PertEstimateCreate
from backend.infrastructure.config.settings import get_settings
from backend.domain.exceptions.pmv1_exceptions import (
    AccesoDenegadoError,
    VersionNoPertenecienteError,
    ConfiguracionPMV1Error,
    CredencialesInvalidasError,
    EstimacionPERTInvalidaError,
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
        "una", "unas", "unos", "y", "ya", "no"
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

    @classmethod
    def is_relevant(
        cls, chunk: dict[str, Any], query: str, keywords: list[str]
    ) -> bool:
        """Evita resultados espurios cuando solo coincide una palabra incidental.

        Una consulta por identificador o frase exacta siempre es relevante. Para
        consultas libres con varias palabras se exige que coincida, como mínimo,
        la mitad de los términos significativos. Así una entrada sin sustento no
        produce normas ni alertas ficticias (CA-HU2.1-03 / CA-HU2.3-02).
        """
        normalized_query = query.strip().lower()
        searchable_parts = (
            str(chunk.get("id", "")),
            str(chunk.get("topic", "")),
            str(chunk.get("content", "")),
            str(chunk.get("document_name", "")),
            str(chunk.get("short_code", "")),
        )
        lowered_parts = tuple(part.lower() for part in searchable_parts)

        if normalized_query and (
            normalized_query == lowered_parts[0]
            or any(normalized_query in part for part in lowered_parts[1:])
        ):
            return True

        if not keywords:
            return False

        searchable_tokens: set[str] = set()
        for part in lowered_parts:
            searchable_tokens.update(re.findall(r"[\wáéíóúüñ]+", part))

        matched = {keyword for keyword in keywords if keyword in searchable_tokens}
        required_matches = 1 if len(keywords) <= 2 else (len(keywords) + 1) // 2
        return len(matched) >= required_matches




class LegalAssessmentEngine:
    """Motor de evaluación y contraste de citas normativas verificables (HU2.2).

    Cumple estrictamente los criterios de aceptación:
    - CA-HU2.2-01: Cuando el sustento identifica un artículo o sección precisa,
      el informe jurídico muestra denominación de la norma, versión, artículo o sección
      y fragmento correspondiente para poder cotejarlo.
    - CA-HU2.2-02: Cuando el material recuperado no permite ubicar el artículo o fragmento
      exacto, el sistema indica 'Cita no verificable' y marca el hallazgo para revisión humana,
      sin inventar un número de artículo ficticio y sin confirmar cumplimiento.
    - Regla de rigor normativo (HU2.2):
      * Si la fuente es un resumen no oficial o un dato simulado, la cita se marca como no verificable.
      * Si el fragmento normativo no contiene el artículo exacto o es apócrifo, se rechaza la pseudovalidación.
      * Si cualquier hallazgo requiere revisión o no es verificable, la evaluación completa
        refleja requires_human_review=True y estado de advertencia.
    """

    @classmethod
    def _verify_exact_article_in_chunk(
        cls,
        claimed_loc: str,
        chunk_content: str,
        chunk_topic: str,
    ) -> tuple[bool, str | None]:
        """Coteja si el artículo o sección alegado existe realmente en el texto o tema del fragmento."""
        if not claimed_loc or not claimed_loc.strip():
            return False, None
        claimed = claimed_loc.strip()
        full_text = f"{chunk_topic} \n {chunk_content}"

        # 1. Coincidencia directa exacta de la cadena
        if claimed.lower() in full_text.lower():
            return True, claimed

        # 2. Búsqueda de números de artículo específicos (evitar falsos positivos como 'Art. 999')
        art_nums = re.findall(r"\b\d+(?:\.\d+)*(?:[a-z])?\b", claimed)
        if art_nums:
            matched_any = False
            for num in art_nums:
                pattern = rf"(?:Art|Arts|Art[ií]culo|Art[ií]culos)?\.?\s*(?:[Nn][°º]\s*)?{re.escape(num)}\b"
                if re.search(pattern, full_text, re.IGNORECASE):
                    matched_any = True
                    break
            if matched_any:
                return True, claimed
            return False, None

        # 3. Numerales romanos o secciones explícitas (e.g. Título III, Art. IV TP)
        roman_match = re.search(
            r"\b(?:T[ií]tulo|Cap[ií]tulo|Art(?:[ií]culo)?\.?)\s+([IVXLCDM]+(?:\s+TP)?)\b",
            claimed,
            re.IGNORECASE,
        )
        if roman_match and roman_match.group(0).lower() in full_text.lower():
            return True, claimed

        # 4. Palabras clave normativas identificables (SINAGERD, Ley DUS, RNE)
        law_match = re.search(r"\b(?:Ley\s+\d+|SINAGERD|RNE\s+[A-Z0-9\.]+)\b", claimed, re.IGNORECASE)
        if law_match and law_match.group(0).lower() in full_text.lower():
            return True, claimed

        return False, None

    @classmethod
    def build_citation(
        cls,
        finding_row: dict[str, Any],
        chunk: dict[str, Any] | None,
    ) -> dict[str, Any]:
        has_precise = bool(finding_row.get("has_precise_reference", True))
        custom_loc = finding_row.get("custom_article_or_section")

        # 1. Caso sin referencia precisa o sin fragmento normativo
        if not has_precise or not chunk:
            return {
                "fragment_id": chunk.get("id") if chunk else None,
                "document_name": chunk.get("document_name") if chunk else "Fuente no especificada",
                "short_code": chunk.get("short_code") if chunk else None,
                "version": chunk.get("version") if chunk else "No determinada",
                "article_or_section": None,  # ESTRICTAMENTE NONE: jamás se fabrica un artículo
                "fragment_content": chunk.get("content") if chunk else None,
                "citation_status": "no_verificable",
                "is_verifiable": False,
                "status_label": "Cita no verificable",
                "limitation_note": (
                    "El sustento no identifica un artículo o sección precisa en la normativa vigente. "
                    "Conforme a CA-HU2.2-02, el hallazgo se marca para revisión humana sin crear un número de artículo ficticio."
                ),
                "in_force": chunk.get("in_force", True) if chunk else False,
                "is_simulated": (chunk.get("data_origin") == "simulated") if chunk else True,
                "data_origin": chunk.get("data_origin", "simulated") if chunk else "simulated",
                "citation_hash": None,
            }

        # 2. Caso norma no vigente / derogada / sustituida
        if not chunk.get("in_force", True):
            return {
                "fragment_id": chunk.get("id"),
                "document_name": chunk.get("document_name"),
                "short_code": chunk.get("short_code"),
                "version": chunk.get("version"),
                "article_or_section": None,  # No aplicable como cita vigente
                "fragment_content": chunk.get("content"),
                "citation_status": "no_verificable",
                "is_verifiable": False,
                "status_label": "Cita no verificable (Norma sustituida o derogada)",
                "limitation_note": (
                    f"La norma '{chunk.get('document_name')}' ({chunk.get('version')}) está marcada como derogada o sustituida. "
                    "No es admisible como sustento legal aplicable para obra pública vigente (CA-HU2.2-02)."
                ),
                "in_force": False,
                "is_simulated": chunk.get("data_origin") == "simulated",
                "data_origin": chunk.get("data_origin", "public"),
                "citation_hash": None,
            }

        # 3. Caso fuente simulada o corpus no oficial (HU2.2)
        # Si la fuente es un resumen no oficial o dato simulado, NO debe marcarse como verificable
        is_simulated_chunk = (
            chunk.get("data_origin") == "simulated"
            or bool(chunk.get("is_simulated", False))
            or bool(finding_row.get("is_simulated", False))
            or chunk.get("data_origin") not in ("public", "oficial", "official")
        )
        if is_simulated_chunk:
            return {
                "fragment_id": chunk.get("id"),
                "document_name": chunk.get("document_name"),
                "short_code": chunk.get("short_code"),
                "version": chunk.get("version"),
                "article_or_section": None,  # No se certifica artículo de fuente simulada
                "fragment_content": chunk.get("content"),
                "citation_status": "no_verificable",
                "is_verifiable": False,
                "status_label": "Cita no verificable (Fuente o corpus simulado)",
                "limitation_note": (
                    "La fuente consultada corresponde a datos simulados o corpus no oficial. "
                    "Conforme a HU2.2, no puede certificarse como cita normativa comprobada ni sustento oficial."
                ),
                "in_force": True,
                "is_simulated": True,
                "data_origin": "simulated",
                "citation_hash": None,
            }

        # 4. Caso norma vigente: resolución y cotejo riguroso del artículo
        chunk_content = str(chunk.get("content", ""))
        chunk_topic = str(chunk.get("topic", ""))

        if custom_loc and str(custom_loc).strip():
            candidate_loc = str(custom_loc).strip()
            # Cotejar si el artículo alegado realmente existe en el fragmento o tema
            is_matched, verified_loc = cls._verify_exact_article_in_chunk(
                candidate_loc, chunk_content, chunk_topic
            )
            if not is_matched:
                return {
                    "fragment_id": chunk.get("id"),
                    "document_name": chunk.get("document_name"),
                    "short_code": chunk.get("short_code"),
                    "version": chunk.get("version"),
                    "article_or_section": None,  # Cita apócrifa o no coincidente: jamás validar
                    "fragment_content": chunk.get("content"),
                    "citation_status": "no_verificable",
                    "is_verifiable": False,
                    "status_label": "Cita no verificable (Artículo no coincide con el fragmento)",
                    "limitation_note": (
                        f"El artículo o acápite alegado ('{candidate_loc}') no coincide ni se encuentra "
                        "en el texto del fragmento normativo oficial. Conforme a HU2.2, se rechaza la pseudovalidación "
                        "y se requiere revisión humana."
                    ),
                    "in_force": True,
                    "is_simulated": False,
                    "data_origin": chunk.get("data_origin", "public"),
                    "citation_hash": None,
                }
            loc = verified_loc or candidate_loc
        else:
            loc = NormativeSearchEngine.resolve_location(chunk)

        # Validar si loc contiene un artículo o sección identificable real y no es genérico
        is_identifiable_loc = bool(
            re.search(
                r"(Art|Título|Titulo|Capítulo|Capitulo|Sección|Seccion|Reglamento|Ley DUS|RNE|SINAGERD|Índice|Indice)",
                loc,
                re.IGNORECASE,
            )
        ) and not loc.startswith("Fragmento ID")

        if not is_identifiable_loc:
            return {
                "fragment_id": chunk.get("id"),
                "document_name": chunk.get("document_name"),
                "short_code": chunk.get("short_code"),
                "version": chunk.get("version"),
                "article_or_section": None,  # Nunca inventar artículo ficticio
                "fragment_content": chunk.get("content"),
                "citation_status": "no_verificable",
                "is_verifiable": False,
                "status_label": "Cita no verificable (Fragmento sin artículo)",
                "limitation_note": (
                    "El fragmento normativo no contiene un artículo, sección o acápite identificable. "
                    "Conforme a CA-HU2.2-02, no se fabrica un número de artículo y se requiere revisión humana."
                ),
                "in_force": True,
                "is_simulated": False,
                "data_origin": chunk.get("data_origin", "public"),
                "citation_hash": None,
            }

        # 5. Caso exitoso: Cita exacta, oficial y comprobable (CA-HU2.2-01)
        citation_raw = f"{chunk['id']}:{chunk.get('version')}:{loc}:{chunk.get('content')}"
        c_hash = hashlib.sha256(citation_raw.encode("utf-8")).hexdigest()

        return {
            "fragment_id": chunk.get("id"),
            "document_name": chunk.get("document_name"),
            "short_code": chunk.get("short_code"),
            "version": chunk.get("version"),
            "article_or_section": loc,
            "fragment_content": chunk.get("content"),
            "citation_status": "verificable",
            "is_verifiable": True,
            "status_label": "Cita exacta y comprobable",
            "limitation_note": None,
            "in_force": True,
            "is_simulated": False,
            "data_origin": chunk.get("data_origin", "public"),
            "citation_hash": c_hash,
        }

    @classmethod
    def evaluate(
        cls,
        project_id: UUID,
        project_code: str,
        project_version_id: UUID | None,
        finding_rows: list[dict[str, Any]],
        chunks_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        assessment_id = uuid4()
        findings_output: list[dict[str, Any]] = []
        verifiable_count = 0
        unverifiable_count = 0

        for r in finding_rows:
            chunk_id = r.get("normative_chunk_id")
            chunk = chunks_by_id.get(str(chunk_id)) if chunk_id else None
            citation = cls.build_citation(r, chunk)

            # Regla de confirmación jurídica: un hallazgo no verificable NUNCA puede estar jurídicamente confirmado
            complies = r.get("complies")
            if not citation["is_verifiable"]:
                complies = None  # abstención / requiere revisión humana
                requires_review = True
            else:
                requires_review = bool(r.get("requires_human_review", False))

            if citation["is_verifiable"]:
                verifiable_count += 1
            else:
                unverifiable_count += 1

            findings_output.append({
                "finding_id": str(r.get("id") or uuid4()),
                "finding_key": r.get("finding_key", "general"),
                "title": r.get("title", "Hallazgo legal"),
                "description": r.get("description", ""),
                "complies": complies,
                "requires_human_review": requires_review,
                "citation": citation,
            })

        total = len(findings_output)
        any_unverifiable = (unverifiable_count > 0)
        any_requires_review = any(f["requires_human_review"] for f in findings_output)
        non_compliant_findings = [f for f in findings_output if f["complies"] is False]

        has_legal_alert = False
        legal_alert_motive = None
        legal_alert_norm = None

        if total == 0:
            status = "insufficient"
            status_label = "Información jurídica insuficiente"
            summary = "El expediente no registra antecedentes jurídicos ni hallazgos normativos vinculados."
            requires_human = True
        elif non_compliant_findings:
            # CA-HU2.3-01: Alerta por posible incompatibilidad sustentada con plan urbano o zona intangible
            first_nc = non_compliant_findings[0]
            has_legal_alert = True
            legal_alert_motive = first_nc.get("description") or first_nc.get("title")
            cit = first_nc.get("citation", {})
            norm_name = cit.get("document_name") or "Normativa territorial"
            art = cit.get("article_or_section") or "Disposición aplicable"
            legal_alert_norm = f"{norm_name} ({art})"

            status = "alerta_legal"
            status_label = "Alerta Legal: Incompatibilidad Normativa/Territorial"
            summary = (
                f"ALERTA LEGAL (HU2.3): Se identificó incompatibilidad con el plan urbano o afectación a zona intangible. "
                f"Sustento normativo: {legal_alert_norm}. Motivo: {legal_alert_motive}. "
                "Conforme a las reglas de control, se bloquea la aprobación definitiva y priorización hasta que la alerta sea resuelta o levantada por Asesoría Jurídica."
            )
            requires_human = True
        elif any_unverifiable or any_requires_review:
            # CA-HU2.3-02: Situación no comprobada -> Requiere revisión (sin alerta legal infundada)
            status = "requires_review"
            status_label = "Requiere revisión humana"
            summary = (
                f"Revisión jurídica preliminar: {verifiable_count} cita(s) exacta(s) y {unverifiable_count} "
                "cita(s) no verificable(s) o pendiente(s) de revisión humana. "
                "Conforme a CA-HU2.3-02, no se formula una alerta legal sin comprobación fehaciente; se requiere cotejo manual por el Asesor Jurídico."
            )
            requires_human = True
        else:
            status = "verified"
            status_label = "Citas normativas verificadas"
            summary = f"Revisión jurídica completa con {verifiable_count} cita(s) exacta(s) y comprobable(s)."
            requires_human = False

        is_any_simulated = any(f["citation"].get("is_simulated", False) for f in findings_output)

        return {
            "assessment_id": str(assessment_id),
            "project_id": str(project_id),
            "project_code": project_code,
            "project_version_id": str(project_version_id) if project_version_id else None,
            "status": status,
            "status_label": status_label,
            "summary": summary,
            "findings": findings_output,
            "total_findings": total,
            "verifiable_citations_count": verifiable_count,
            "unverifiable_citations_count": unverifiable_count,
            "requires_human_review": requires_human,
            "has_legal_alert": has_legal_alert,
            "legal_alert_motive": legal_alert_motive,
            "legal_alert_norm": legal_alert_norm,
            "is_resolved": False,
            "resolution_justification": None,
            "evaluated_at": datetime.now(timezone.utc),
            "is_simulated_corpus": is_any_simulated,
        }

class PertDurationEngine:
    """Motor de cálculo y validación de estimación de duración de obra e incertidumbre (PERT) - HU1.9.

    Criterios de aceptación:
    - CA-HU1.9-01: Duración esperada con fórmula (a + 4m + b)/6, desviación estándar (b - a)/6,
      varianza ((b - a)/6)², e indicación expresa de estimación referencial y no plazo garantizado.
    - CA-HU1.9-02: Validación estricta de completitud, números finitos y 0 <= a <= m <= b,
      señalando con precisión qué valor debe corregirse y por qué.
    """

    FORMULA_APPLIED = (
        "Duración esperada: μ = (a + 4m + b) / 6; "
        "Desviación estándar (incertidumbre): σ = (b - a) / 6; "
        "Varianza: σ² = ((b - a) / 6)²"
    )

    DISCLAIMER = (
        "La duración calculada bajo metodología PERT representa una aproximación probabilística sujeta a "
        "variabilidad e incertidumbre durante la ejecución de la obra. No constituye compromiso contractual "
        "ni plazo garantizado de entrega. Esta estimación no reemplaza la programación detallada de obra ni "
        "el cronograma vinculante de ejecución."
    )

    @classmethod
    def validate_inputs(
        cls,
        optimistic: Any,
        most_likely: Any,
        pessimistic: Any,
        time_unit: str = "meses",
    ) -> tuple[Decimal, Decimal, Decimal, str]:
        """Valida que a, m, b estén completos, sean números finitos y cumplan 0 <= a <= m <= b."""
        # 1. Completitud
        if optimistic is None:
            raise EstimacionPERTInvalidaError(
                "Falta ingresar la duración optimista (a).",
                campo="optimistic_duration",
                motivo="Falta el valor de duración optimista (a). Debe ser un número mayor o igual a 0.",
            )
        if most_likely is None:
            raise EstimacionPERTInvalidaError(
                "Falta ingresar la duración más probable (m).",
                campo="most_likely_duration",
                motivo="Falta el valor de duración más probable (m). Debe cumplir a <= m <= b.",
            )
        if pessimistic is None:
            raise EstimacionPERTInvalidaError(
                "Falta ingresar la duración pesimista (b).",
                campo="pessimistic_duration",
                motivo="Falta el valor de duración pesimista (b). Debe cumplir m <= b.",
            )

        # 2. Conversión a Decimal y verificación de finitud
        try:
            a_val = float(optimistic)
            if math.isnan(a_val) or math.isinf(a_val):
                raise ValueError()
            a_dec = Decimal(str(optimistic)).quantize(Decimal("0.0001"))
        except Exception:
            raise EstimacionPERTInvalidaError(
                "La duración optimista (a) debe ser un número finito válido.",
                campo="optimistic_duration",
                motivo="El valor ingresado para la duración optimista no es un número finito.",
            )

        try:
            m_val = float(most_likely)
            if math.isnan(m_val) or math.isinf(m_val):
                raise ValueError()
            m_dec = Decimal(str(most_likely)).quantize(Decimal("0.0001"))
        except Exception:
            raise EstimacionPERTInvalidaError(
                "La duración más probable (m) debe ser un número finito válido.",
                campo="most_likely_duration",
                motivo="El valor ingresado para la duración más probable no es un número finito.",
            )

        try:
            b_val = float(pessimistic)
            if math.isnan(b_val) or math.isinf(b_val):
                raise ValueError()
            b_dec = Decimal(str(pessimistic)).quantize(Decimal("0.0001"))
        except Exception:
            raise EstimacionPERTInvalidaError(
                "La duración pesimista (b) debe ser un número finito válido.",
                campo="pessimistic_duration",
                motivo="El valor ingresado para la duración pesimista no es un número finito.",
            )

        # 3. No negatividad (0 <= a, 0 <= m, 0 <= b)
        if a_dec < Decimal("0"):
            raise EstimacionPERTInvalidaError(
                f"La duración optimista (a = {a_dec:.2f}) no puede ser negativa; debe ser mayor o igual a 0.",
                campo="optimistic_duration",
                motivo="La duración optimista no puede ser un valor negativo.",
            )
        if m_dec < Decimal("0"):
            raise EstimacionPERTInvalidaError(
                f"La duración más probable (m = {m_dec:.2f}) no puede ser negativa; debe ser mayor o igual a 0.",
                campo="most_likely_duration",
                motivo="La duración más probable no puede ser un valor negativo.",
            )
        if b_dec < Decimal("0"):
            raise EstimacionPERTInvalidaError(
                f"La duración pesimista (b = {b_dec:.2f}) no puede ser negativa; debe ser mayor o igual a 0.",
                campo="pessimistic_duration",
                motivo="La duración pesimista no puede ser un valor negativo.",
            )

        # 4. Orden jerárquico 0 <= a <= m <= b
        if a_dec > m_dec:
            raise EstimacionPERTInvalidaError(
                f"Orden inválido: la duración optimista (a = {a_dec:.2f}) no puede ser mayor que la duración más probable (m = {m_dec:.2f}).",
                campo="optimistic_duration",
                motivo=f"La estimación optimista ({a_dec:.2f}) supera a la más probable ({m_dec:.2f}), violando la condición a <= m.",
            )
        if m_dec > b_dec:
            raise EstimacionPERTInvalidaError(
                f"Orden inválido: la duración más probable (m = {m_dec:.2f}) no puede ser mayor que la duración pesimista (b = {b_dec:.2f}).",
                campo="most_likely_duration",
                motivo=f"La estimación más probable ({m_dec:.2f}) supera a la pesimista ({b_dec:.2f}), violando la condición m <= b.",
            )
        if a_dec > b_dec:
            raise EstimacionPERTInvalidaError(
                f"Orden inválido: la duración optimista (a = {a_dec:.2f}) no puede ser mayor que la duración pesimista (b = {b_dec:.2f}).",
                campo="pessimistic_duration",
                motivo=f"La estimación optimista ({a_dec:.2f}) supera a la pesimista ({b_dec:.2f}), violando la condición a <= b.",
            )

        clean_unit = time_unit.strip().lower() if time_unit and time_unit.strip() else "meses"
        if clean_unit not in ("meses", "días", "dias", "semanas"):
            clean_unit = "meses"
        if clean_unit == "dias":
            clean_unit = "días"

        return a_dec, m_dec, b_dec, clean_unit

    @classmethod
    def calculate(
        cls,
        optimistic: Decimal,
        most_likely: Decimal,
        pessimistic: Decimal,
        time_unit: str = "meses",
    ) -> dict[str, Any]:
        """Calcula duración esperada PERT, desviación estándar, varianza e intervalo."""
        six = Decimal("6")
        expected = (optimistic + (Decimal("4") * most_likely) + pessimistic) / six
        std_dev = (pessimistic - optimistic) / six
        variance = std_dev * std_dev

        interval_low = expected - std_dev
        if interval_low < Decimal("0"):
            interval_low = Decimal("0")
        interval_high = expected + std_dev

        explanation = (
            f"Duración esperada PERT: ({optimistic:.2f} + 4×{most_likely:.2f} + {pessimistic:.2f}) / 6 = {expected:.2f} {time_unit}. "
            f"Incertidumbre (desviación estándar PERT): ({pessimistic:.2f} - {optimistic:.2f}) / 6 = ±{std_dev:.2f} {time_unit}. "
            f"Varianza del plazo: {variance:.4f} {time_unit}². "
            f"Rango esperado (μ ± σ): [{interval_low:.2f}, {interval_high:.2f}] {time_unit}."
        )

        return {
            "time_unit": time_unit,
            "optimistic_duration": optimistic,
            "most_likely_duration": most_likely,
            "pessimistic_duration": pessimistic,
            "expected_duration": expected,
            "standard_deviation": std_dev,
            "variance": variance,
            "confidence_interval_low": interval_low,
            "confidence_interval_high": interval_high,
            "formula_applied": cls.FORMULA_APPLIED,
            "disclaimer": cls.DISCLAIMER,
            "explanation": explanation,
        }

class RiskCheckpointEngine:
    """Motor de gestión de puntos de control (checkpoints) y pausas de flujo ante riesgos altos (HU3.1).

    Criterios cumplidos:
    - CA-HU3.1-01: Si una evaluación detecta un riesgo alto configurado para revisión humana,
      el sistema detiene el procesamiento en un punto de control persistente, establece el estado
      'Pendiente de revisión' (pending_review) y no continúa automáticamente hacia la finalización.
    - CA-HU3.1-02: Si no hay riesgo alto (riesgo bajo o moderado, sin causa de revisión), el flujo
      continúa normalmente hacia la siguiente etapa sin solicitar revisión humana innecesaria.
    """

    PAUSE_RISK_LEVELS: ClassVar[set[str]] = {"high"}

    @classmethod
    def detect_high_risk_condition(
        cls,
        conn: psycopg.Connection,
        project_version_id: UUID,
    ) -> dict[str, Any] | None:
        """Detecta si la versión del expediente cumple una condición configurada de riesgo alto.

        CA-HU3.4-01: Evita que el mismo riesgo ya autorizado vuelva a crear la misma pausa,
        sin ignorar riesgos nuevos o evaluaciones en nuevas versiones.
        """
        with conn.cursor(row_factory=dict_row) as cur:
            # Consultar si existen puntos de control ya autorizados y resueltos para esta versión específica
            resolved_cps = cur.execute(
                """
                SELECT id, risk_source, reason, details
                FROM evaluation_checkpoints
                WHERE project_version_id = %s AND status = 'resolved'
                """,
                (project_version_id,),
            ).fetchall()

            # 1. Comprobar evaluaciones ambientales registradas para la versión
            row = cur.execute(
                """
                SELECT id, project_id, project_version_id, risk_level, risk_observation,
                       requires_human_review, declared_vs_evidence_json, impacts_json
                FROM environmental_assessments
                WHERE project_version_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (project_version_id,),
            ).fetchone()

        if row:
            if row["risk_level"] in cls.PAUSE_RISK_LEVELS and row.get("requires_human_review"):
                declared_ev = row.get("declared_vs_evidence_json") or {}
                prox = declared_ev.get("proximity_to_water_meters")
                in_risk = declared_ev.get("is_in_protected_or_risk_area")

                cause_items = []
                if prox is not None and float(prox) < 50.0:
                    cause_items.append(f"Proximidad crítica a cuerpo de agua ({float(prox):.1f} m < 50 m reglamentarios)")
                if in_risk:
                    cause_items.append("Emplazamiento en zona clasificada de riesgo territorial o faja marginal intangible")

                cause = (
                    f"Causa técnica de pausa: Riesgo ambiental alto por {'; '.join(cause_items)}."
                    if cause_items
                    else "Causa técnica de pausa: Detección de condición de riesgo ambiental territorial alto."
                )

                verifiable = declared_ev.get("verifiable_evidence")
                if verifiable and verifiable.strip():
                    obs = f"Comprobación técnica requerida: {verifiable.strip()} Requiere verificar delimitación física de faja marginal y sustento de mitigación formal."
                elif row.get("risk_observation") and row["risk_observation"].strip() != cause:
                    obs = row["risk_observation"].strip()
                else:
                    obs = "Observación pendiente de aclaración"

                env_id_str = str(row["id"])
                # Comprobar si este riesgo específico ya fue resuelto y autorizado por la Gerencia en esta versión
                is_already_authorized = any(
                    cp["risk_source"] == "environmental"
                    and (
                        (isinstance(cp["details"], dict) and cp["details"].get("environmental_assessment_id") == env_id_str)
                        or cp["reason"] == cause
                    )
                    for cp in resolved_cps
                )

                if not is_already_authorized:
                    return {
                        "risk_source": "environmental",
                        "risk_source_label": "Impacto ambiental territorial (Recurso hídrico / Ecosistema)",
                        "risk_level": row["risk_level"],
                        "risk_level_label": "Riesgo Alto",
                        "reason": cause,
                        "details": {
                            "environmental_assessment_id": env_id_str,
                            "risk_level": row["risk_level"],
                            "cause": cause,
                            "observation": obs,
                            "risk_observation": obs,
                            "requires_human_review": True,
                            "declared_vs_evidence": declared_ev,
                        },
                    }
            # Si ya existe una evaluación formal registrada para esta versión y no es de riesgo alto
            # (o el riesgo ya fue formalmente resuelto), no hereda riesgos ni registros de versiones anteriores.
            return None

        # 2. Si aún no existe fila en environmental_assessments, inspeccionar project_environmental_records
        # asegurando que solo aplique a registros de esta versión específica (o v1 si es retrocompatible)
        with conn.cursor(row_factory=dict_row) as cur:
            rec_row = cur.execute(
            """
            SELECT r.id, r.project_id, r.environmental_component, r.declared_impacts,
                   r.verifiable_evidence, r.proximity_to_water_meters, r.is_in_protected_or_risk_area,
                   r.source_name
            FROM project_environmental_records r
            JOIN project_versions pv ON pv.id = %s
            WHERE (
                (r.project_version_id = pv.id)
                OR (r.project_version_id IS NULL AND r.project_id = pv.project_id AND pv.version_number = 1)
            ) AND (
                r.is_in_protected_or_risk_area = TRUE
                OR (r.proximity_to_water_meters IS NOT NULL AND r.proximity_to_water_meters < 50.0)
            )
            LIMIT 1
            """,
            (project_version_id,),
        ).fetchone()

        if rec_row:
            cause_text = (
                f"Causa técnica de pausa: Componente '{rec_row['environmental_component']}'. "
                f"Distancia crítica a cuerpo de agua ({rec_row['proximity_to_water_meters']} m < 50 m reglamentarios) en zona clasificada de riesgo territorial."
            )
            obs_text = (
                f"Comprobación técnica requerida: {rec_row['verifiable_evidence']}. Requiere verificar delimitación física y sustento de mitigaciones aprobado por ANA."
                if rec_row.get("verifiable_evidence")
                else "Observación pendiente de aclaración"
            )

            rec_id_str = str(rec_row["id"])
            is_rec_already_authorized = any(
                cp["risk_source"] == "environmental"
                and (
                    (isinstance(cp["details"], dict) and cp["details"].get("record_id") == rec_id_str)
                    or cp["reason"] == cause_text
                )
                for cp in resolved_cps
            )

            if not is_rec_already_authorized:
                return {
                    "risk_source": "environmental",
                    "risk_source_label": "Impacto ambiental territorial (Recurso hídrico / Ecosistema)",
                    "risk_level": "high",
                    "risk_level_label": "Riesgo Alto",
                    "reason": cause_text,
                    "details": {
                        "record_id": rec_id_str,
                        "component": rec_row["environmental_component"],
                        "proximity_to_water_meters": float(rec_row["proximity_to_water_meters"]) if rec_row["proximity_to_water_meters"] else None,
                        "is_in_protected_or_risk_area": rec_row["is_in_protected_or_risk_area"],
                        "source_name": rec_row["source_name"],
                        "cause": cause_text,
                        "observation": obs_text,
                        "risk_observation": obs_text,
                    },
                }

        return None

    @classmethod
    def get_active_checkpoint(
        cls,
        conn: psycopg.Connection,
        project_version_id: UUID,
    ) -> dict[str, Any] | None:
        """Recupera el punto de control pendiente activo para la versión específica del expediente (HU3.1 / HU3.2)."""
        row = conn.execute(
            """
            SELECT id AS checkpoint_id, project_id, project_version_id, evaluation_id,
                   checkpoint_type, status, reason, risk_source, risk_level, details,
                   resolved_by_user_id, resolution_motive, resolution_conditions, resolved_at,
                   created_at, updated_at
            FROM evaluation_checkpoints
            WHERE project_version_id = %s AND status = 'pending_review'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_version_id,),
        ).fetchone()

        if not row:
            return None

        details = row["details"] if isinstance(row["details"], dict) else {}

        # 1. Causa específica de la pausa
        raw_cause = details.get("cause") or row.get("reason")
        cause = raw_cause.strip() if isinstance(raw_cause, str) and raw_cause.strip() else None

        # 2. Observación concreta que requiere revisión humana
        # Buscar en details exclusivamente por la observación de revisión humana
        raw_obs = details.get("observation") or details.get("risk_observation")
        if not raw_obs and isinstance(details.get("declared_vs_evidence"), dict):
            raw_obs = details["declared_vs_evidence"].get("verifiable_evidence")

        # REGLA HU3.2: NO copiar 'cause' a 'observation' cuando esta última falte.
        # Mostrar 'Observación pendiente de aclaración' y conservar el estado pendiente.
        if raw_obs and isinstance(raw_obs, str) and raw_obs.strip():
            # Si raw_obs es idéntico a cause (datos previos no diferenciados)
            if raw_obs.strip() == (cause or "").strip() and isinstance(details.get("declared_vs_evidence"), dict):
                verifiable = details["declared_vs_evidence"].get("verifiable_evidence")
                if verifiable and isinstance(verifiable, str) and verifiable.strip():
                    observation = f"Comprobación técnica requerida: {verifiable.strip()}"
                else:
                    observation = "Observación pendiente de aclaración"
            else:
                observation = raw_obs.strip()
        else:
            observation = "Observación pendiente de aclaración"

        fallback_cause = "Información incompleta: La causa técnica específica de la pausa no se encuentra registrada."
        reason_text = cause or fallback_cause

        return {
            "checkpoint_id": row["checkpoint_id"],
            "project_id": row["project_id"],
            "project_version_id": row["project_version_id"],
            "evaluation_id": row["evaluation_id"],
            "checkpoint_type": row["checkpoint_type"],
            "status": row["status"],
            "status_label": "Pendiente de revisión",
            "reason": reason_text,
            "cause": cause,
            "observation": observation,
            "risk_source": row["risk_source"] or "no_especificado",
            "risk_source_label": {
                "environmental": "Impacto ambiental territorial (Recurso hídrico / Ecosistema)",
                "legal": "Conformidad jurídica / Citas normativas",
            }.get(row["risk_source"], row["risk_source"] or "Origen no especificado"),
            "risk_level": row["risk_level"] or "high",
            "risk_level_label": {
                "high": "Riesgo Alto",
                "moderate": "Riesgo Moderado",
                "low": "Riesgo Bajo",
            }.get(row["risk_level"], row["risk_level"] or "Riesgo Alto"),
            "requires_human_review": True,
            "allows_final_approval": False,
            "details": details,
            "resolved_by_user_id": row.get("resolved_by_user_id"),
            "resolution_motive": row.get("resolution_motive"),
            "resolution_conditions": row.get("resolution_conditions"),
            "resolved_at": row.get("resolved_at"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @classmethod
    def get_latest_checkpoint(
        cls,
        conn: psycopg.Connection,
        project_version_id: UUID,
    ) -> dict[str, Any] | None:
        """Recupera el último punto de control (pendiente o resuelto) para la versión del expediente (HU3.4)."""
        row = conn.execute(
            """
            SELECT id AS checkpoint_id, project_id, project_version_id, evaluation_id,
                   checkpoint_type, status, reason, risk_source, risk_level, details,
                   resolved_by_user_id, resolution_motive, resolution_conditions, resolved_at,
                   created_at, updated_at
            FROM evaluation_checkpoints
            WHERE project_version_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_version_id,),
        ).fetchone()

        if not row:
            return None

        details = row["details"] if isinstance(row["details"], dict) else {}
        raw_cause = details.get("cause") or row.get("reason")
        cause = raw_cause.strip() if isinstance(raw_cause, str) and raw_cause.strip() else None

        raw_obs = details.get("observation") or details.get("risk_observation")
        if not raw_obs and isinstance(details.get("declared_vs_evidence"), dict):
            raw_obs = details["declared_vs_evidence"].get("verifiable_evidence")

        if raw_obs and isinstance(raw_obs, str) and raw_obs.strip():
            if raw_obs.strip() == (cause or "").strip() and isinstance(details.get("declared_vs_evidence"), dict):
                verifiable = details["declared_vs_evidence"].get("verifiable_evidence")
                if verifiable and isinstance(verifiable, str) and verifiable.strip():
                    observation = f"Comprobación técnica requerida: {verifiable.strip()}"
                else:
                    observation = "Observación pendiente de aclaración"
            else:
                observation = raw_obs.strip()
        else:
            observation = "Observación pendiente de aclaración"

        is_pending = (row["status"] == "pending_review")
        return {
            "checkpoint_id": row["checkpoint_id"],
            "project_id": row["project_id"],
            "project_version_id": row["project_version_id"],
            "evaluation_id": row["evaluation_id"],
            "checkpoint_type": row["checkpoint_type"],
            "status": row["status"],
            "status_label": "Pendiente de revisión" if is_pending else "Reanudado / Resuelto",
            "reason": cause or (row.get("reason") or "Información no especificada"),
            "cause": cause,
            "observation": observation,
            "risk_source": row["risk_source"] or "no_especificado",
            "risk_source_label": {
                "environmental": "Impacto ambiental territorial (Recurso hídrico / Ecosistema)",
                "legal": "Conformidad jurídica / Citas normativas",
            }.get(row["risk_source"], row["risk_source"]),
            "risk_level": row["risk_level"],
            "risk_level_label": {
                "high": "Riesgo Alto",
                "moderate": "Riesgo Moderado",
                "low": "Riesgo Bajo",
            }.get(row["risk_level"], row["risk_level"]),
            "requires_human_review": is_pending,
            "allows_final_approval": not is_pending,
            "details": details,
            "resolved_by_user_id": row.get("resolved_by_user_id"),
            "resolution_motive": row.get("resolution_motive"),
            "resolution_conditions": row.get("resolution_conditions"),
            "resolved_at": row.get("resolved_at"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @classmethod
    def has_pending_checkpoint(
        cls,
        conn: psycopg.Connection,
        project_version_id: UUID,
    ) -> bool:
        """Indica si existe un punto de control pendiente de revisión en la versión."""
        return cls.get_active_checkpoint(conn, project_version_id) is not None

    @classmethod
    def create_or_get_checkpoint(
        cls,
        conn: psycopg.Connection,
        project_id: UUID,
        project_version_id: UUID,
        evaluation_id: UUID | None,
        risk_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Crea o recupera idempotentemente el punto de control persistente."""
        checkpoint_id = uuid4()
        row = conn.execute(
            """
            INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, evaluation_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'high_risk_pause', 'pending_review', %s, %s, %s, %s, now(), now())
            ON CONFLICT (project_version_id, risk_source, checkpoint_type) DO UPDATE SET
                status = 'pending_review',
                evaluation_id = COALESCE(EXCLUDED.evaluation_id, evaluation_checkpoints.evaluation_id),
                reason = EXCLUDED.reason,
                risk_level = EXCLUDED.risk_level,
                details = EXCLUDED.details,
                updated_at = now()
            RETURNING id, project_id, project_version_id, evaluation_id, checkpoint_type,
                      status, reason, risk_source, risk_level, details, created_at, updated_at
            """,
            (
                checkpoint_id,
                project_id,
                project_version_id,
                evaluation_id,
                risk_info["reason"],
                risk_info["risk_source"],
                risk_info["risk_level"],
                Jsonb(risk_info.get("details", {})),
            ),
        ).fetchone()

        # Actualizar estado del proyecto a 'pending_review'
        conn.execute(
            "UPDATE projects SET status = 'pending_review', updated_at = now() WHERE id = %s",
            (project_id,),
        )

        # Si hay evaluación asociada, pausarla
        if evaluation_id:
            conn.execute(
                """
                UPDATE evaluations
                SET status = 'pending_review', error_message = %s
                WHERE id = %s
                """,
                (risk_info["reason"], evaluation_id),
            )

        # Registrar evento de auditoría
        conn.execute(
            """
            INSERT INTO audit_events
            (action, entity_type, entity_id, details)
            VALUES ('EVALUATION_PAUSED_HIGH_RISK', 'evaluation_checkpoint', %s, %s)
            """,
            (
                row["id"],
                Jsonb(
                    {
                        "project_id": str(project_id),
                        "project_version_id": str(project_version_id),
                        "evaluation_id": str(evaluation_id) if evaluation_id else None,
                        "risk_source": risk_info["risk_source"],
                        "risk_level": risk_info["risk_level"],
                        "reason": risk_info["reason"],
                    }
                ),
            ),
        )

        return {
            "checkpoint_id": row["id"],
            "project_id": row["project_id"],
            "project_version_id": row["project_version_id"],
            "evaluation_id": row["evaluation_id"],
            "checkpoint_type": row["checkpoint_type"],
            "status": row["status"],
            "status_label": "Pendiente de revisión",
            "reason": row["reason"],
            "risk_source": row["risk_source"],
            "risk_source_label": {
                "environmental": "Impacto ambiental territorial (Recurso hídrico / Ecosistema)",
                "legal": "Conformidad jurídica / Citas normativas",
            }.get(row["risk_source"], row["risk_source"]),
            "risk_level": row["risk_level"],
            "risk_level_label": {
                "high": "Riesgo Alto",
                "moderate": "Riesgo Moderado",
                "low": "Riesgo Bajo",
            }.get(row["risk_level"], row["risk_level"]),
            "requires_human_review": True,
            "allows_final_approval": False,
            "details": row["details"] if isinstance(row["details"], dict) else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


class TechnicalFeasibilityEngine:
    """Motor de evaluación de viabilidad técnica de proyectos (HU1.8 - PMV2 Sprint 2).

    Criterios de Aceptación:
    - CA-HU1.8-01: Verificación técnica sustentada. Identifica cada criterio verificado,
      su estado y el sustento disponible, presentándolo como OPINIÓN PRELIMINAR automatizada,
      sin atribuirle valor de certificación profesional (ni sustituye la firma de ingenieros
      colegiados Ley 28858 / RNE).
    - CA-HU1.8-02: Incumplimiento u observación técnica. Si un criterio no se cumple según
      los datos aportados o presenta condicionamientos técnicos, señala cuál está observado,
      el motivo técnico y qué debe corregir o revisar el planificador con recomendaciones
      no prescriptivas solicitando evaluación del profesional responsable.
    - CA-HU1.8-03: Imposibilidad de emitir conclusión. Si faltan datos indispensables para
      comprobar un criterio, o si los datos provienen de fuentes simuladas sin comprobación física,
      indica 'Información insuficiente' o 'Pendiente de revisión técnica' y NO declara viable al proyecto.
      El puntaje técnico resultante es estrictamente None (cero falsos positivos; no entrega puntajes
      ficticios a HU1.12).
    """

    PRELIMINARY_OPINION_DISCLAIMER: ClassVar[str] = (
        "ADVERTENCIA DE CONTROL Y ALCANCE LEGAL: Esta evaluación técnica constituye una opinión preliminar automatizada "
        "basada en los parámetros y documentos registrados en la plataforma. No tiene carácter de certificación profesional, "
        "no constituye liquidación ni conformidad de obra, y no sustituye la responsabilidad funcional ni la firma colegiada "
        "de los ingenieros especialistas responsables (Ley N.° 28858 y Reglamento Nacional de Edificaciones - RNE)."
    )

    CANONICAL_CRITERIA: ClassVar[tuple[dict[str, str], ...]] = (
        {
            "code": "mecanica_suelos",
            "name": "Capacidad portante y mecánica de suelos",
            "normative_reference": 'RNE Norma Técnica E.050 "Suelos y Cimentaciones" (R.M. N.° 406-2018-VIVIENDA)',
            "normative_version": "2018 (actualizada)",
            "applied_rule": "Estudio de Mecánica de Suelos (EMS) conforme a RNE E.050 (Art. 13-15). La capacidad portante y tipo de cimentación requieren validación por el especialista geotécnico según las cargas del proyecto.",
        },
        {
            "code": "servicios_basicos",
            "name": "Factibilidad de servicios básicos de agua y saneamiento",
            "normative_reference": "Directiva General Invierte.pe (D.L. 1252) y RNE Norma Técnica OS.010",
            "normative_version": "2019 (vigente)",
            "applied_rule": "Factibilidad de servicios de agua y saneamiento otorgada por la EPS prestadora (SEDAM Huancayo), con punto de empalme certificado y sin condicionamientos técnicos pendientes.",
        },
        {
            "code": "topografia_taludes",
            "name": "Pendiente topográfica y estabilidad física de terreno",
            "normative_reference": 'RNE Norma Técnica CE.020 "Estabilización de Suelos y Taludes" y CENEPRED',
            "normative_version": "2012 (vigente)",
            "applied_rule": "Levantamiento topográfico perimétrico-altimétrico y evaluación de estabilidad física conforme a RNE CE.020 y CENEPRED.",
        },
        {
            "code": "dimensionamiento_predio",
            "name": "Dimensionamiento y compatibilidad de lote normativo",
            "normative_reference": "Plan de Desarrollo Metropolitano Huancayo 2017-2037 (O.M. N.° 636-MPH) y RNE A.010",
            "normative_version": "2017 (vigente)",
            "applied_rule": "Compatibilidad de uso y dimensionamiento normativo de predio conforme al PDM Huancayo 2017-2037 y RNE A.010.",
        },
    )

    @classmethod
    def evaluate_criterion(cls, meta: dict[str, str], row: dict[str, Any] | None) -> dict[str, Any]:
        code = meta["code"]
        name = meta["name"]
        norm_ref = meta["normative_reference"]
        norm_ver = meta["normative_version"]
        applied_rule = meta["applied_rule"]

        # Caso 1: Datos insuficientes o no registrados
        if (
            not row
            or not row.get("has_sufficient_data")
            or (row.get("parameter_value_numeric") is None and not row.get("parameter_value_text"))
        ):
            if code == "mecanica_suelos":
                explanation = "Falta estudio de mecánica de suelos (EMS) suscrito por ingeniero civil/geotécnico colegiado."
                guidance = "Adjuntar Informe Técnico de Mecánica de Suelos con fines de cimentación conforme a la Norma E.050 del RNE, suscrito por profesional habilitado (CIP)."
            elif code == "servicios_basicos":
                explanation = "No se dispone de certificado de factibilidad de servicios de agua y saneamiento emitido por la EPS prestadora (SEDAM Huancayo)."
                guidance = "Gestionar y anexar el Certificado de Factibilidad de Servicios de Agua Potable y Alcantarillado emitido por SEDAM Huancayo o la entidad prestadora correspondiente."
            elif code == "topografia_taludes":
                explanation = "Falta levantamiento topográfico perimétrico con curvas de nivel o evaluación de estabilidad de taludes."
                guidance = "Adjuntar plano topográfico perimétrico y altimétrico firmado por ingeniero civil o topógrafo colegiado, con curvas de nivel y cálculo de pendiente media."
            elif code == "dimensionamiento_predio":
                explanation = "Falta partida registral, plano de independización o certificado de parámetros urbanísticos que acredite dimensionamiento y zonificación."
                guidance = "Presentar Partida Registral SUNARP saneada o Certificado de Parámetros Urbanísticos y Edificatorios emitido por la Municipalidad Distrital de El Tambo."
            else:
                explanation = f"Faltan datos técnicos o sustento documental indispensable para el criterio {name}."
                guidance = "Registrar la información técnica requerida y adjuntar el documento sustentatorio de respaldo."

            return {
                "criterion_code": code,
                "criterion_name": name,
                "normative_reference": norm_ref,
                "normative_version": norm_ver,
                "has_sufficient_data": False,
                "parameter_name": row.get("parameter_name") if row else None,
                "parameter_value_numeric": None,
                "parameter_unit": row.get("parameter_unit") if row else None,
                "parameter_value_text": None,
                "applied_rule": applied_rule,
                "supporting_document": None,
                "source_origin": row.get("source_origin") if row else "simulated",
                "is_simulated": row.get("is_simulated", True) if row else True,
                "status": "informacion_insuficiente",
                "status_label": "Información insuficiente",
                "explanation": explanation,
                "correction_guidance": guidance,
            }

        val_num = float(row["parameter_value_numeric"]) if row.get("parameter_value_numeric") is not None else None
        val_txt = row.get("parameter_value_text")
        unit = row.get("parameter_unit") or ""
        doc = row.get("supporting_document")
        origin = row.get("source_origin") or "simulated"
        is_sim = row.get("is_simulated", True)
        param_name = row.get("parameter_name")

        # Caso 2: Criterio observado (por incompatibilidad de capacidad portante o condicionamiento de servicios)
        is_observed = False
        obs_explanation = ""
        obs_guidance = ""

        if code == "mecanica_suelos":
            if val_num is not None and val_num < 0.80:
                is_observed = True
                obs_explanation = (
                    f"Capacidad portante admisible informada ({val_num:.2f} {unit}) es baja para cimentación superficial directa convencional. "
                    "El suelo presenta limitaciones de capacidad de carga según los sondeos informados."
                )
                obs_guidance = (
                    "El ingeniero especialista en geotecnia y estructuras responsable del proyecto debe evaluar y proponer la solución "
                    "técnica adecuada (dimensionamiento de cimentación, mejoramiento de suelo o alternativas estructurales) conforme al EMS."
                )

        elif code == "servicios_basicos":
            txt_lower = (val_txt or "").lower()
            if "condiciona" in txt_lower or "no factible" in txt_lower or "ampliación" in txt_lower or (val_num is not None and val_num > 100.0):
                is_observed = True
                obs_explanation = (
                    f"Factibilidad de servicios condicionada: SEDAM Huancayo reporta que la conexión no es inmediata ({val_txt or f'distancia {val_num:.2f} m'}). "
                    "Requiere infraestructura complementaria o ampliación de colector."
                )
                obs_guidance = (
                    "Gestionar con la EPS prestadora (SEDAM Huancayo) las condiciones técnicas de empalme e incorporar los componentes "
                    "de saneamiento requeridos en el expediente del proyecto."
                )

        elif code == "topografia_taludes":
            if val_num is not None and val_num > 25.0:
                is_observed = True
                obs_explanation = (
                    f"Pendiente media del terreno informada ({val_num:.2f} {unit}) es pronunciada y presenta riesgo potencial de inestabilidad física o desprendimiento."
                )
                obs_guidance = (
                    "El profesional responsable de geotecnia/topografía debe realizar un estudio de estabilidad de taludes y plantear "
                    "obras de sostenimiento físico (muros de contención o banquetas de estabilización) conforme a RNE CE.020."
                )

        elif code == "dimensionamiento_predio":
            is_width = "metro" in unit.lower() or "m" == unit.strip()
            threshold = 6.0 if is_width else 200.0
            if val_num is not None and val_num < threshold:
                is_observed = True
                obs_explanation = (
                    f"Dimensión informada ({val_num:.2f} {unit}) es reducida respecto al programa arquitectónico tentativo o sección de faja vial requerida."
                )
                obs_guidance = (
                    "El planificador y arquitecto proyectista deben revisar la compatibilidad del anteproyecto con el área útil del predio "
                    "o gestionar servidumbres/ampliaciones según el PDM Huancayo y RNE A.010."
                )

        if is_observed:
            return {
                "criterion_code": code,
                "criterion_name": name,
                "normative_reference": norm_ref,
                "normative_version": norm_ver,
                "has_sufficient_data": True,
                "parameter_name": param_name,
                "parameter_value_numeric": val_num,
                "parameter_unit": unit,
                "parameter_value_text": val_txt,
                "applied_rule": applied_rule,
                "supporting_document": doc,
                "source_origin": origin,
                "is_simulated": is_sim,
                "status": "observado",
                "status_label": "Observado",
                "explanation": obs_explanation,
                "correction_guidance": obs_guidance,
            }

        # Caso 3: Parámetro simulado sin comprobación física
        if is_sim:
            val_display = f"{val_num:.2f} {unit}" if val_num is not None else (val_txt or "Registrado")
            return {
                "criterion_code": code,
                "criterion_name": name,
                "normative_reference": norm_ref,
                "normative_version": norm_ver,
                "has_sufficient_data": True,
                "parameter_name": param_name,
                "parameter_value_numeric": val_num,
                "parameter_unit": unit,
                "parameter_value_text": val_txt,
                "applied_rule": applied_rule,
                "supporting_document": doc,
                "source_origin": origin,
                "is_simulated": True,
                "status": "simulado_no_verificado",
                "status_label": "Sustento no comprobado (simulado)",
                "explanation": (
                    f"El parámetro registrado ({val_display}) corresponde a un dato simulado para demostración del flujo. "
                    "El documento referenciado no está comprobado en el archivo físico del expediente ni constituye certificación profesional."
                ),
                "correction_guidance": (
                    "Presentar el documento técnico oficial original suscrito por el ingeniero especialista colegiado (CIP) "
                    "para su cotejo y verificación en el expediente municipal."
                ),
            }

        # Caso 4: Parámetro real verificado y conforme
        val_display = f"{val_num:.2f} {unit}" if val_num is not None else (val_txt or "Registrado")
        return {
            "criterion_code": code,
            "criterion_name": name,
            "normative_reference": norm_ref,
            "normative_version": norm_ver,
            "has_sufficient_data": True,
            "parameter_name": param_name,
            "parameter_value_numeric": val_num,
            "parameter_unit": unit,
            "parameter_value_text": val_txt,
            "applied_rule": applied_rule,
            "supporting_document": doc,
            "source_origin": origin,
            "is_simulated": False,
            "status": "cumple",
            "status_label": "Cumple con sustento verificado",
            "explanation": f"Parámetro técnico ({val_display}) cotejado con documento de sustento verificable ({doc}) y validado conforme a normativa aplicable.",
            "correction_guidance": None,
        }

    @classmethod
    def evaluate(
        cls,
        project_id: UUID,
        project_code: str,
        project_version_id: UUID,
        version_number: int,
        parameter_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rows_by_code = {r["criterion_code"]: r for r in parameter_rows}
        evaluated_criteria: list[dict[str, Any]] = []

        for meta in cls.CANONICAL_CRITERIA:
            row = rows_by_code.get(meta["code"])
            item = cls.evaluate_criterion(meta, row)
            evaluated_criteria.append(item)

        total = len(evaluated_criteria)
        cumple_count = sum(1 for c in evaluated_criteria if c["status"] == "cumple")
        observado_count = sum(1 for c in evaluated_criteria if c["status"] == "observado")
        insuficiente_count = sum(1 for c in evaluated_criteria if c["status"] == "informacion_insuficiente")
        simulado_count = sum(1 for c in evaluated_criteria if c["status"] == "simulado_no_verificado")

        criteria_summary = {
            "total": total,
            "cumple": cumple_count,
            "observado": observado_count,
            "informacion_insuficiente": insuficiente_count,
            "simulado_no_verificado": simulado_count,
        }

        # Reglas de dictamen global (cero falsos positivos)
        if insuficiente_count > 0:
            overall_result = "informacion_insuficiente"
            overall_result_label = "Información insuficiente"
            is_viable = False
            technical_score = None
            score_explanation = (
                "Puntaje técnico no determinado: existen criterios técnicos con información insuficiente "
                "que impiden una cuantificación objetiva (CA-HU1.8-03)."
            )
            summary = (
                f"Evaluación técnica preliminar inconclusa: {insuficiente_count} de {total} criterios carecen "
                "de información técnica indispensable o sustento en el expediente. No se declara la viabilidad técnica del proyecto."
            )
            dimension_conclusion = "No viable preliminarmente por falta de información técnica indispensable."
            dimension_justification = (
                f"El expediente presenta {insuficiente_count} criterio(s) con información técnica faltante o insuficiente. "
                "Conforme al principio de precaución técnica y CA-HU1.8-03, no es posible emitir una calificación de viabilidad "
                "hasta subsanar los parámetros técnicos requeridos."
            )
        elif observado_count > 0:
            overall_result = "observado"
            overall_result_label = "Observado"
            is_viable = False
            technical_score = None
            score_explanation = (
                f"Puntaje técnico no determinado: se identificaron {observado_count} observación(es) técnica(s) "
                "que requieren evaluación del profesional responsable antes de cualquier ponderación cuantitativa."
            )
            summary = (
                f"Evaluación técnica preliminar con observaciones: {observado_count} de {total} criterios presentan "
                "incompatibilidades o condicionamientos técnicos que deben ser subsanados por los especialistas del proyecto."
            )
            dimension_conclusion = "No viable preliminarmente por observaciones técnicas críticas no subsanadas."
            dimension_justification = (
                f"Se identificaron {observado_count} observación(es) técnica(s) relativas a los parámetros evaluados. "
                "El proyecto no califica como viable hasta que el profesional responsable incorpore las medidas técnicas recomendadas."
            )
        elif simulado_count > 0:
            overall_result = "pendiente_revision"
            overall_result_label = "Pendiente de revisión técnica"
            is_viable = False
            technical_score = None
            score_explanation = (
                "Puntaje técnico no determinado: los parámetros provienen de registros simulados de demostración "
                "sin sustento documental comprobado en el expediente físico (CA-HU1.8-01 / CA-HU1.8-03)."
            )
            summary = (
                "Preevaluación técnica en modo demostración: Los parámetros registrados corresponden a datos simulados "
                "y no cuentan con sustento documental comprobado en el archivo físico del expediente. "
                "Conforme a las reglas de control, no se otorga calificación de viabilidad ni puntaje numérico "
                "hasta contar con estudios oficiales verificados y suscritos por ingenieros colegiados (CIP)."
            )
            dimension_conclusion = "Pendiente de verificación técnica presencial/documental."
            dimension_justification = (
                "Los antecedentes del expediente contienen parámetros simulados para fines de demostración del software. "
                "No constituyen prueba documental verificable ni habilitan certificación técnica de viabilidad."
            )
        else:
            overall_result = "cumple"
            overall_result_label = "Viable preliminarmente"
            is_viable = True
            technical_score = 100.0
            score_explanation = (
                f"Puntaje técnico de 100.0/100: todos los criterios técnicos reglamentarios ({total}/{total}) "
                "cuentan con sustento documental verificado y cumplen los requerimientos de ingeniería aplicables."
            )
            summary = (
                "Evaluación técnica preliminar favorable: todos los criterios técnicos analizados cumplen "
                "con la normativa vigente y cuentan con sustento documental verificado en el expediente."
            )
            dimension_conclusion = "Viable preliminarmente conforme a los parámetros técnicos evaluados."
            dimension_justification = (
                "Todos los parámetros evaluados cuentan con sustento documental verificable y cumplen con los "
                "criterios de ingeniería del RNE y la normativa municipal aplicable."
            )

        now = datetime.now(timezone.utc)

        return {
            "project_id": project_id,
            "project_code": project_code,
            "project_version_id": project_version_id,
            "version_number": version_number,
            "status": "completed",
            "overall_result": overall_result,
            "overall_result_label": overall_result_label,
            "is_viable": is_viable,
            "is_preliminary_opinion": True,
            "disclaimer": cls.PRELIMINARY_OPINION_DISCLAIMER,
            "summary": summary,
            "criteria_summary": criteria_summary,
            "criteria": evaluated_criteria,
            "technical_score": technical_score,
            "score_explanation": score_explanation,
            "dimension_conclusion": dimension_conclusion,
            "dimension_justification": dimension_justification,
            "evaluated_at": now,
        }


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

    def create_project_version(
        self,
        project_id: UUID,
        title: str,
        description: str,
        location_description: str,
        proposed_land_use: str,
        estimated_budget_pen: Decimal,
        beneficiaries_count: int,
        actor_id: UUID,
        territorial_data_origin: str = "declared",
    ) -> dict[str, Any]:
        """Crea una nueva versión de un proyecto (ej. v2 replanteada/mitigada) y actualiza el estado almacenado a 'ready' (operación de escritura)."""
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            p_row = conn.execute(
                "SELECT id FROM projects WHERE id = %s",
                (project_id,),
            ).fetchone()
            if not p_row:
                raise RecursoPMV1NoEncontradoError("Proyecto no encontrado")

            max_v = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) AS max_v FROM project_versions WHERE project_id = %s",
                (project_id,),
            ).fetchone()["max_v"]
            next_version = max_v + 1
            version_id = uuid4()
            now = datetime.now(timezone.utc)

            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description,
                 location_description, proposed_land_use, territorial_data_origin,
                 estimated_budget_pen, beneficiaries_count, created_by_user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    version_id,
                    project_id,
                    next_version,
                    title,
                    description,
                    location_description,
                    proposed_land_use,
                    territorial_data_origin,
                    estimated_budget_pen,
                    beneficiaries_count,
                    actor_id,
                    now,
                ),
            )
            # En la operación de escritura correspondiente, se actualiza el estado del proyecto a 'ready' para la versión nueva
            conn.execute(
                "UPDATE projects SET status = 'ready', updated_at = %s WHERE id = %s",
                (now, project_id),
            )
            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'PROJECT_VERSION_CREATED', 'project_version', %s, %s)
                """,
                (
                    actor_id,
                    version_id,
                    Jsonb({"project_id": str(project_id), "version_number": next_version}),
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
            checkpoint = RiskCheckpointEngine.get_active_checkpoint(conn, row["project_version_id"])
            pert_estimate = self._get_pert_estimate_with_conn(conn, row["project_version_id"])
            res = dict(row)

            # HU3.2 (Estrictamente de lectura): Determinar el estado efectivo para la versión vigente del expediente.
            # No ejecuta sentencias UPDATE en projects ni muta evaluaciones, checkpoints, auditoría ni fechas.
            if checkpoint is not None:
                # Caso 2: La versión vigente posee un punto de control activo de riesgo alto.
                res["status"] = "pending_review"
            elif res["status"] == "pending_review":
                # projects.status en base de datos figura en 'pending_review',
                # pero la versión vigente NO tiene punto de control activo registrado.
                is_subsequent = row["version_number"] > 1
                has_prior_checkpoint = False
                if is_subsequent:
                    has_prior_checkpoint = bool(
                        conn.execute(
                            """
                            SELECT 1 FROM evaluation_checkpoints ec
                            JOIN project_versions pv ON pv.id = ec.project_version_id
                            WHERE pv.project_id = %s
                              AND pv.version_number < %s
                              AND ec.status = 'pending_review'
                            LIMIT 1
                            """,
                            (project_id, row["version_number"]),
                        ).fetchone()
                    )

                # Verificar si la versión vigente tiene una evaluación en 'pending_review'
                current_eval_paused = bool(
                    conn.execute(
                        """
                        SELECT 1 FROM evaluations
                        WHERE project_version_id = %s AND status = 'pending_review'
                        LIMIT 1
                        """,
                        (row["project_version_id"],),
                    ).fetchone()
                )

                if is_subsequent and has_prior_checkpoint and not current_eval_paused:
                    # Caso 1: Versión 1 pausada y Versión 2 (o superior) mitigada/replanteada.
                    # El estado efectivo de la versión vigente se deriva de sus propias evaluaciones sin mutar la BD:
                    eval_row = conn.execute(
                        """
                        SELECT status FROM evaluations
                        WHERE project_version_id = %s
                        ORDER BY requested_at DESC LIMIT 1
                        """,
                        (row["project_version_id"],),
                    ).fetchone()
                    if eval_row and eval_row["status"] == "completed":
                        effective_status = "evaluated"
                    elif eval_row and eval_row["status"] in ("queued", "processing"):
                        effective_status = "evaluating"
                    else:
                        effective_status = "ready"

                    res["status"] = effective_status
                    checkpoint = None
                else:
                    # Caso 3: Inconsistencia de datos.
                    # El expediente figura en 'pending_review' (o evaluación pausada) sin registro de checkpoint
                    # activo para la versión vigente, y no corresponde a una versión posterior con pausa histórica.
                    # REGLA: No convertir automáticamente a 'ready' ni habilitar una aprobación sin revisión.
                    # Mantener estrictamente 'pending_review' e informar la inconsistencia de forma controlada.
                    res["status"] = "pending_review"
                    created_at_dt = row.get("updated_at") or row.get("created_at") or datetime.now(timezone.utc)
                    checkpoint = {
                        "checkpoint_id": None,
                        "project_id": project_id,
                        "project_version_id": row["project_version_id"],
                        "evaluation_id": None,
                        "checkpoint_type": "inconsistent_data_review",
                        "status": "pending_review",
                        "status_label": "Pendiente de revisión",
                        "reason": (
                            "Inconsistencia de control: El expediente figura en estado 'Pendiente de revisión' "
                            "sin registro de punto de control activo para la versión vigente. "
                            "Requiere aclaración técnica y auditoría antes de continuar."
                        ),
                        "cause": "Inconsistencia de control: Estado 'Pendiente de revisión' sin punto de control registrado",
                        "observation": (
                            "Observación pendiente de aclaración: Se requiere auditoría y comprobación técnica del expediente "
                            "para subsanar el registro antes de permitir cualquier aprobación o procesamiento."
                        ),
                        "risk_source": "inconsistent_state",
                        "risk_source_label": "Auditoría de consistencia de datos",
                        "risk_level": "high",
                        "risk_level_label": "Riesgo Alto",
                        "requires_human_review": True,
                        "allows_final_approval": False,
                        "details": {
                            "inconsistent": True,
                            "inconsistency_type": "pending_review_missing_checkpoint",
                            "message": "Expediente en estado 'pending_review' sin checkpoint activo.",
                        },
                        "created_at": created_at_dt,
                        "updated_at": created_at_dt,
                    }

            res["checkpoint"] = checkpoint
            res["pert_estimate"] = pert_estimate
            res["technical_assessment"] = self._get_technical_assessment_with_conn(conn, row["project_version_id"])
            return res


    def _get_pert_estimate_with_conn(
        self, conn: psycopg.Connection[Any], project_version_id: UUID
    ) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT id, project_id, project_version_id, registered_by_user_id, time_unit,
                   optimistic_duration, most_likely_duration, pessimistic_duration,
                   expected_duration, standard_deviation, variance,
                   confidence_interval_low, confidence_interval_high,
                   formula_applied, disclaimer, explanation, created_at, updated_at
            FROM project_pert_estimates
            WHERE project_version_id = %s
            """,
            (project_version_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def get_pert_estimate(
        self, project_id: UUID, project_version_id: UUID | None = None
    ) -> dict[str, Any] | None:
        """Recupera la estimación de duración PERT para la versión del expediente (HU1.9)."""
        project = self.get_project(project_id)
        target_version_id = UUID(str(project_version_id)) if project_version_id else project["project_version_id"]
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            if project_version_id is not None:
                self._verify_version_belongs_to_project(conn, project_id, target_version_id)
            return self._get_pert_estimate_with_conn(conn, target_version_id)

    def _get_technical_assessment_with_conn(
        self, conn: psycopg.Connection[Any], project_version_id: UUID
    ) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT ta.id, ta.project_id, p.code AS project_code, ta.project_version_id, pv.version_number,
                   ta.status, ta.overall_result, ta.overall_result_label, ta.is_viable,
                   ta.is_preliminary_opinion, ta.disclaimer, ta.summary,
                   ta.criteria_summary, ta.findings_json, ta.technical_score,
                   ta.score_explanation, ta.dimension_conclusion, ta.dimension_justification,
                   ta.evaluated_at
            FROM technical_feasibility_assessments ta
            JOIN projects p ON p.id = ta.project_id
            JOIN project_versions pv ON pv.id = ta.project_version_id
            WHERE ta.project_version_id = %s
            """,
            (project_version_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "assessment_id": row["id"],
            "project_id": row["project_id"],
            "project_code": row["project_code"],
            "project_version_id": row["project_version_id"],
            "version_number": row["version_number"],
            "status": row["status"],
            "overall_result": row["overall_result"],
            "overall_result_label": row["overall_result_label"],
            "is_viable": row["is_viable"],
            "is_preliminary_opinion": row["is_preliminary_opinion"],
            "disclaimer": row["disclaimer"],
            "summary": row["summary"],
            "criteria_summary": row["criteria_summary"],
            "criteria": row["findings_json"],
            "technical_score": float(row["technical_score"]) if row["technical_score"] is not None else None,
            "score_explanation": row["score_explanation"],
            "dimension_conclusion": row["dimension_conclusion"],
            "dimension_justification": row["dimension_justification"],
            "evaluated_at": row["evaluated_at"],
            "duplicated": False,
        }

    def evaluate_technical_feasibility(
        self,
        project_id: UUID,
        actor_id: UUID,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta y persiste la preevaluación de viabilidad técnica del expediente para su versión vigente (HU1.8)."""
        project = self.get_project(project_id)
        project_version_id = project["project_version_id"]
        version_number = project["version_number"]
        cleaned_key = (idempotency_key or "").strip() or None

        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de viabilidad técnica no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            # 1. Comprobar Idempotency-Key
            if cleaned_key:
                prev = conn.execute(
                    """
                    SELECT ta.id, ta.project_id, p.code AS project_code, ta.project_version_id,
                           pv.version_number, ta.status, ta.overall_result, ta.overall_result_label,
                           ta.is_viable, ta.is_preliminary_opinion, ta.disclaimer, ta.summary,
                           ta.criteria_summary, ta.findings_json, ta.technical_score,
                           ta.score_explanation, ta.dimension_conclusion, ta.dimension_justification,
                           ta.evaluated_at, ta.idempotency_key
                    FROM technical_feasibility_assessments ta
                    JOIN projects p ON p.id = ta.project_id
                    JOIN project_versions pv ON pv.id = ta.project_version_id
                    WHERE ta.idempotency_key = %s
                    """,
                    (cleaned_key,),
                ).fetchone()
                if prev:
                    if prev["project_id"] != project_id:
                        raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")
                    return {
                        "assessment_id": prev["id"],
                        "project_id": prev["project_id"],
                        "project_code": prev["project_code"],
                        "project_version_id": prev["project_version_id"],
                        "version_number": prev["version_number"],
                        "status": prev["status"],
                        "overall_result": prev["overall_result"],
                        "overall_result_label": prev["overall_result_label"],
                        "is_viable": prev["is_viable"],
                        "is_preliminary_opinion": prev["is_preliminary_opinion"],
                        "disclaimer": prev["disclaimer"],
                        "summary": prev["summary"],
                        "criteria_summary": prev["criteria_summary"],
                        "criteria": prev["findings_json"],
                        "technical_score": float(prev["technical_score"]) if prev["technical_score"] is not None else None,
                        "score_explanation": prev["score_explanation"],
                        "dimension_conclusion": prev["dimension_conclusion"],
                        "dimension_justification": prev["dimension_justification"],
                        "evaluated_at": prev["evaluated_at"],
                        "duplicated": True,
                    }

            # 2. Leer parámetros técnicos registrados para esta versión
            param_rows = conn.execute(
                """
                SELECT id, project_id, project_version_id, criterion_code, criterion_name,
                       normative_reference, normative_version, has_sufficient_data,
                       parameter_name, parameter_value_numeric, parameter_unit, parameter_value_text,
                       applied_rule, supporting_document, source_origin, is_simulated
                FROM project_technical_parameters
                WHERE project_version_id = %s
                ORDER BY criterion_code ASC
                """,
                (project_version_id,),
            ).fetchall()

            # 3. Evaluar con el motor técnico
            assessment = TechnicalFeasibilityEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=project_version_id,
                version_number=version_number,
                parameter_rows=[dict(r) for r in param_rows],
            )

            assessment_id = uuid4()
            effective_key = cleaned_key or f"tech-assessment-{assessment_id}"
            now = assessment["evaluated_at"]

            # 4. Insertar o actualizar la evaluación para esta versión
            saved_row = conn.execute(
                """
                INSERT INTO technical_feasibility_assessments
                (id, project_id, project_version_id, requested_by_user_id, idempotency_key,
                 status, overall_result, overall_result_label, is_viable, is_preliminary_opinion,
                 disclaimer, summary, criteria_summary, findings_json, technical_score,
                 score_explanation, dimension_conclusion, dimension_justification, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_version_id) DO UPDATE SET
                    idempotency_key = EXCLUDED.idempotency_key,
                    requested_by_user_id = EXCLUDED.requested_by_user_id,
                    status = EXCLUDED.status,
                    overall_result = EXCLUDED.overall_result,
                    overall_result_label = EXCLUDED.overall_result_label,
                    is_viable = EXCLUDED.is_viable,
                    is_preliminary_opinion = EXCLUDED.is_preliminary_opinion,
                    disclaimer = EXCLUDED.disclaimer,
                    summary = EXCLUDED.summary,
                    criteria_summary = EXCLUDED.criteria_summary,
                    findings_json = EXCLUDED.findings_json,
                    technical_score = EXCLUDED.technical_score,
                    score_explanation = EXCLUDED.score_explanation,
                    dimension_conclusion = EXCLUDED.dimension_conclusion,
                    dimension_justification = EXCLUDED.dimension_justification,
                    evaluated_at = EXCLUDED.evaluated_at
                RETURNING id
                """,
                (
                    assessment_id,
                    project_id,
                    project_version_id,
                    actor_id,
                    effective_key,
                    assessment["status"],
                    assessment["overall_result"],
                    assessment["overall_result_label"],
                    assessment["is_viable"],
                    assessment["is_preliminary_opinion"],
                    assessment["disclaimer"],
                    assessment["summary"],
                    Jsonb(assessment["criteria_summary"]),
                    Jsonb(assessment["criteria"]),
                    Decimal(str(assessment["technical_score"])) if assessment["technical_score"] is not None else None,
                    assessment["score_explanation"],
                    assessment["dimension_conclusion"],
                    assessment["dimension_justification"],
                    now,
                ),
            ).fetchone()
            actual_assessment_id = saved_row["id"] if saved_row else assessment_id

            # 5. Registrar evento de auditoría
            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'TECHNICAL_ASSESSMENT_COMPLETED', 'technical_assessment', %s, %s)
                """,
                (
                    actor_id,
                    actual_assessment_id,
                    Jsonb(
                        {
                            "project_id": str(project_id),
                            "project_code": project["code"],
                            "project_version_id": str(project_version_id),
                            "overall_result": assessment["overall_result"],
                            "is_viable": assessment["is_viable"],
                            "technical_score": assessment["technical_score"],
                            "criteria_summary": assessment["criteria_summary"],
                        }
                    ),
                ),
            )

        return {
            "assessment_id": actual_assessment_id,
            **assessment,
            "duplicated": False,
        }

    def get_technical_feasibility(
        self, project_id: UUID, version_id: UUID | None = None
    ) -> dict[str, Any] | None:
        """Obtiene la evaluación técnica de la versión vigente (o la especificada) de forma estrictamente de lectura."""
        if not _is_db_available(self.db_url):
            if not self.enable_demo_fallback:
                raise ServicioNoDisponibleError(
                    "Servicio de viabilidad técnica no disponible: la base de datos no responde."
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            target_version_id = version_id
            if target_version_id is None:
                pv = conn.execute(
                    "SELECT id FROM project_versions WHERE project_id = %s ORDER BY version_number DESC LIMIT 1",
                    (project_id,),
                ).fetchone()
                if not pv:
                    raise RecursoPMV1NoEncontradoError("Expediente no encontrado")
                target_version_id = pv["id"]
            else:
                pv = conn.execute(
                    "SELECT 1 FROM project_versions WHERE id = %s AND project_id = %s",
                    (target_version_id, project_id),
                ).fetchone()
                if not pv:
                    raise VersionNoPertenecienteError(
                        "La versión especificada no pertenece al expediente indicado"
                    )

            return self._get_technical_assessment_with_conn(conn, target_version_id)

    def _verify_version_belongs_to_project(
        self, conn: psycopg.Connection[Any], project_id: UUID, version_id: UUID
    ) -> None:
        """Comprueba que project_version_id pertenece a project_id. Lanza VersionNoPertenecienteError si no."""
        row = conn.execute(
            "SELECT 1 FROM project_versions WHERE id = %s AND project_id = %s",
            (version_id, project_id),
        ).fetchone()
        if not row:
            raise VersionNoPertenecienteError(
                f"La versión {version_id} no pertenece al expediente {project_id}. "
                "Operación rechazada sin modificar ninguna estimación.",
                project_id=str(project_id),
                version_id=str(version_id),
            )

    def register_pert_estimate(
        self,
        project_id: UUID,
        actor_id: UUID,
        data: PertEstimateCreate | dict[str, Any],
    ) -> dict[str, Any]:
        """Calcula y persiste la estimación de duración PERT e incertidumbre vinculada a la versión (HU1.9)."""
        project = self.get_project(project_id)
        if isinstance(data, dict):
            req_version_id = data.get("project_version_id")
            opt = data.get("optimistic_duration")
            ml = data.get("most_likely_duration")
            pess = data.get("pessimistic_duration")
            t_unit = data.get("time_unit", "meses")
        else:
            req_version_id = data.project_version_id
            opt = data.optimistic_duration
            ml = data.most_likely_duration
            pess = data.pessimistic_duration
            t_unit = data.time_unit

        version_id = UUID(str(req_version_id)) if req_version_id else project["project_version_id"]

        a, m, b, unit = PertDurationEngine.validate_inputs(
            optimistic=opt,
            most_likely=ml,
            pessimistic=pess,
            time_unit=t_unit,
        )

        calc = PertDurationEngine.calculate(
            optimistic=a,
            most_likely=m,
            pessimistic=b,
            time_unit=unit,
        )

        estimate_id = uuid4()
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            self._verify_version_belongs_to_project(conn, project_id, version_id)
            row = conn.execute(
                """
                INSERT INTO project_pert_estimates
                (id, project_id, project_version_id, registered_by_user_id, time_unit,
                 optimistic_duration, most_likely_duration, pessimistic_duration,
                 expected_duration, standard_deviation, variance,
                 confidence_interval_low, confidence_interval_high,
                 formula_applied, disclaimer, explanation, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (project_version_id) DO UPDATE SET
                    registered_by_user_id = EXCLUDED.registered_by_user_id,
                    time_unit = EXCLUDED.time_unit,
                    optimistic_duration = EXCLUDED.optimistic_duration,
                    most_likely_duration = EXCLUDED.most_likely_duration,
                    pessimistic_duration = EXCLUDED.pessimistic_duration,
                    expected_duration = EXCLUDED.expected_duration,
                    standard_deviation = EXCLUDED.standard_deviation,
                    variance = EXCLUDED.variance,
                    confidence_interval_low = EXCLUDED.confidence_interval_low,
                    confidence_interval_high = EXCLUDED.confidence_interval_high,
                    formula_applied = EXCLUDED.formula_applied,
                    disclaimer = EXCLUDED.disclaimer,
                    explanation = EXCLUDED.explanation,
                    updated_at = now()
                RETURNING id, project_id, project_version_id, registered_by_user_id, time_unit,
                          optimistic_duration, most_likely_duration, pessimistic_duration,
                          expected_duration, standard_deviation, variance,
                          confidence_interval_low, confidence_interval_high,
                          formula_applied, disclaimer, explanation, created_at, updated_at
                """,
                (
                    estimate_id,
                    project_id,
                    version_id,
                    actor_id,
                    unit,
                    calc["optimistic_duration"],
                    calc["most_likely_duration"],
                    calc["pessimistic_duration"],
                    calc["expected_duration"],
                    calc["standard_deviation"],
                    calc["variance"],
                    calc["confidence_interval_low"],
                    calc["confidence_interval_high"],
                    calc["formula_applied"],
                    calc["disclaimer"],
                    calc["explanation"],
                ),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'PERT_ESTIMATE_REGISTERED', 'project_pert_estimate', %s, %s)
                """,
                (
                    actor_id,
                    row["id"],
                    Jsonb(
                        {
                            "project_id": str(project_id),
                            "project_version_id": str(version_id),
                            "time_unit": unit,
                            "a": str(calc["optimistic_duration"]),
                            "m": str(calc["most_likely_duration"]),
                            "b": str(calc["pessimistic_duration"]),
                            "expected": str(calc["expected_duration"]),
                            "std_dev": str(calc["standard_deviation"]),
                        }
                    ),
                ),
            )

        return dict(row)

    def _verify_planner_actor(self, actor_id: UUID) -> None:
        """Verifica que el usuario tenga rol de Gerente/Planificador (PLANNER) o Administrador (ADMIN) en auth_db (HU3.4)."""
        settings = get_settings()
        auth_dsn = _dsn(settings.auth_db_url)
        with psycopg.connect(auth_dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT r.code
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_id = r.id
                WHERE u.id = %s
                """,
                (actor_id,),
            ).fetchall()
            roles = {r["code"] for r in rows}
            if not (roles & {"PLANNER", "ADMIN", "SUPERADMIN"}):
                raise AccesoDenegadoError(
                    f"El usuario {actor_id} no cuenta con perfil de Gerente de Planeamiento o Administrador. "
                    "Se requiere rol PLANNER o ADMIN para autorizar la reanudación del checkpoint."
                )

    def resume_project_checkpoint(
        self,
        project_id: UUID,
        actor_id: UUID,
        justification: str,
        conditions: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Reanuda la evaluación desde un punto de control HITL persistente autorizado por Gerencia (HU3.4).

        Cumple estrictamente los criterios de aceptación:
        - CA-HU3.4-01: Con pausa persistida y decisión válida de un responsable autorizado, continúa desde el
          checkpoint, conserva los resultados anteriores y no repite etapas ya completadas.
        - CA-HU3.4-02: Sin autorización válida o con un usuario sin permiso, rechaza la reanudación y conserva 'Pendiente de revisión'.
        - CA-HU3.4-03: Si hubo cambios sustanciales o una versión nueva del expediente, no reutiliza la aprobación anterior.
        """
        cleaned_key = idempotency_key.strip()
        if not cleaned_key:
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")

        cleaned_justification = justification.strip() if justification else ""
        if len(cleaned_justification) < 5:
            raise ConfiguracionPMV1Error("La justificación de reanudación debe tener al menos 5 caracteres")

        cleaned_conditions = conditions.strip() if conditions and conditions.strip() else None

        # CA-HU3.4-02: Verificar que el usuario tenga rol autorizado
        self._verify_planner_actor(actor_id)

        project = self.get_project(project_id)
        version_id = project["project_version_id"]

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            # 1. Comprobación de idempotencia estricta
            prev = conn.execute(
                """
                SELECT id AS checkpoint_id, project_id, project_version_id, evaluation_id, status,
                       resolved_by_user_id, resolution_motive, resolution_conditions, resolved_at, idempotency_key
                FROM evaluation_checkpoints
                WHERE idempotency_key = %s
                """,
                (cleaned_key,),
            ).fetchone()

            if prev:
                if prev["project_id"] != project_id or prev["project_version_id"] != version_id:
                    raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente o versión")
                if prev["resolution_motive"] != cleaned_justification:
                    raise ConfiguracionPMV1Error("Idempotency-Key no puede ser reutilizada con justificación distinta")
                return {
                    "checkpoint_id": prev["checkpoint_id"],
                    "project_id": prev["project_id"],
                    "project_version_id": prev["project_version_id"],
                    "evaluation_id": prev["evaluation_id"],
                    "status": "resolved",
                    "status_label": "Reanudado / Resuelto",
                    "resolved_by_user_id": prev["resolved_by_user_id"],
                    "resolution_motive": prev["resolution_motive"],
                    "resolution_conditions": prev["resolution_conditions"],
                    "resolved_at": prev["resolved_at"],
                    "project_status": project["status"],
                    "duplicated": True,
                    "message": "Evaluación ya reanudada previamente con esta clave de idempotencia.",
                }

            # 2. Buscar checkpoint para la versión vigente
            cp_row = conn.execute(
                """
                SELECT id AS checkpoint_id, project_id, project_version_id, evaluation_id, status,
                       reason, risk_source, risk_level, details, resolved_by_user_id, resolution_motive,
                       resolution_conditions, resolved_at
                FROM evaluation_checkpoints
                WHERE project_version_id = %s AND checkpoint_type = 'high_risk_pause'
                ORDER BY created_at DESC
                LIMIT 1
                FOR UPDATE
                """,
                (version_id,),
            ).fetchone()

            if not cp_row:
                raise RecursoPMV1NoEncontradoError(
                    f"No existe un punto de control (checkpoint) para la versión vigente ({version_id}) del expediente."
                )

            if cp_row["status"] == "resolved":
                raise ConfiguracionPMV1Error(
                    "El punto de control ya ha sido resuelto o reanudado previamente. "
                    "No se puede reanudar nuevamente sin un nuevo punto de control activo."
                )

            if cp_row["status"] != "pending_review":
                raise ConfiguracionPMV1Error(
                    f"El punto de control se encuentra en estado '{cp_row['status']}', no en 'pending_review'."
                )

            now = datetime.now(timezone.utc)
            checkpoint_id = cp_row["checkpoint_id"]
            evaluation_id = cp_row["evaluation_id"]

            # 3. Actualizar checkpoint a resolved
            conn.execute(
                """
                UPDATE evaluation_checkpoints
                SET status = 'resolved',
                    resolved_by_user_id = %s,
                    resolution_motive = %s,
                    resolution_conditions = %s,
                    resolved_at = %s,
                    idempotency_key = %s,
                    updated_at = %s
                WHERE id = %s AND status = 'pending_review'
                """,
                (
                    actor_id,
                    cleaned_justification,
                    cleaned_conditions,
                    now,
                    cleaned_key,
                    now,
                    checkpoint_id,
                ),
            )

            # 4. CA-HU3.4-01: Conservar resultados anteriores y continuar procesamiento de la etapa pendiente
            target_eval_id = evaluation_id
            if not target_eval_id:
                ev_find = conn.execute(
                    """
                    SELECT id FROM evaluations
                    WHERE project_version_id = %s
                    ORDER BY requested_at DESC LIMIT 1
                    """,
                    (version_id,),
                ).fetchone()
                if ev_find:
                    target_eval_id = ev_find["id"]

            if target_eval_id:
                # Comprobar si economic_result_projections ya existe
                proj_exists = conn.execute(
                    "SELECT 1 FROM economic_result_projections WHERE evaluation_id = %s",
                    (target_eval_id,),
                ).fetchone()

                if not proj_exists:
                    # Procesar la etapa pendiente exactamente una vez
                    ev_data = conn.execute(
                        """
                        SELECT e.id AS evaluation_id, e.criteria_version_id,
                               pv.estimated_budget_pen, pv.beneficiaries_count,
                               cv.excellent_cost_pen, cv.unacceptable_cost_pen
                        FROM evaluations e
                        JOIN project_versions pv ON pv.id = e.project_version_id
                        LEFT JOIN criteria_versions cv ON cv.id = e.criteria_version_id
                        WHERE e.id = %s
                        """,
                        (target_eval_id,),
                    ).fetchone()

                    if ev_data:
                        excellent = ev_data.get("excellent_cost_pen")
                        unacceptable = ev_data.get("unacceptable_cost_pen")
                        if excellent is None or unacceptable is None:
                            act_cv = conn.execute(
                                "SELECT id, excellent_cost_pen, unacceptable_cost_pen FROM criteria_versions WHERE status = 'active' LIMIT 1"
                            ).fetchone()
                            if act_cv:
                                excellent = act_cv["excellent_cost_pen"]
                                unacceptable = act_cv["unacceptable_cost_pen"]
                                conn.execute(
                                    "UPDATE evaluations SET criteria_version_id = %s WHERE id = %s",
                                    (act_cv["id"], target_eval_id),
                                )

                        budget = Decimal(str(ev_data["estimated_budget_pen"]))
                        beneficiaries = int(ev_data["beneficiaries_count"])
                        exc_dec = Decimal(str(excellent))
                        unacc_dec = Decimal(str(unacceptable))

                        cost, score = EconomicProcessor.calculate(budget, beneficiaries, exc_dec, unacc_dec)
                        assessment_id = uuid4()
                        explanation = (
                            f"Costo por beneficiario = S/ {budget} / {beneficiaries} = S/ {cost}. "
                            f"Umbrales: excelente S/ {exc_dec}, inaceptable S/ {unacc_dec}; score {score}/100. "
                            "Procesado tras reanudación autorizada de checkpoint."
                        )
                        conn.execute(
                            """
                            INSERT INTO economic_result_projections
                            (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100,
                             status, explanation, algorithm_version, received_at)
                            VALUES (%s, %s, %s, %s, 'completed', %s, 'economic-cost-per-beneficiary-v1', %s)
                            ON CONFLICT (evaluation_id) DO UPDATE SET
                                cost_per_beneficiary_pen = EXCLUDED.cost_per_beneficiary_pen,
                                score_0_100 = EXCLUDED.score_0_100,
                                status = 'completed',
                                explanation = EXCLUDED.explanation,
                                received_at = EXCLUDED.received_at
                            """,
                            (target_eval_id, assessment_id, cost, score, explanation, now),
                        )

                # Declarar completed únicamente cuando exista su resultado en economic_result_projections
                has_proj = conn.execute(
                    "SELECT 1 FROM economic_result_projections WHERE evaluation_id = %s",
                    (target_eval_id,),
                ).fetchone()

                if has_proj:
                    conn.execute(
                        """
                        UPDATE evaluations
                        SET status = 'completed', finished_at = %s, error_message = NULL
                        WHERE id = %s
                        """,
                        (now, target_eval_id),
                    )

            if target_eval_id and not has_proj:
                raise ConfiguracionPMV1Error(
                    "No se pudo completar la etapa económica pendiente; el expediente continúa en revisión."
                )
            next_project_status = "evaluated" if target_eval_id else "ready"
            conn.execute(
                "UPDATE projects SET status = %s, updated_at = %s WHERE id = %s",
                (next_project_status, now, project_id),
            )

            # 5. Persistir auditoría de la decisión
            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'CHECKPOINT_RESUMED', 'evaluation_checkpoint', %s, %s)
                """,
                (
                    actor_id,
                    checkpoint_id,
                    Jsonb({
                        "project_id": str(project_id),
                        "project_version_id": str(version_id),
                        "evaluation_id": str(evaluation_id) if evaluation_id else None,
                        "resolution_motive": cleaned_justification,
                        "resolution_conditions": cleaned_conditions,
                        "resumed_at": now.isoformat(),
                    }),
                ),
            )

        return {
            "checkpoint_id": checkpoint_id,
            "project_id": project_id,
            "project_version_id": version_id,
            "evaluation_id": evaluation_id,
            "status": "resolved",
            "status_label": "Reanudado / Resuelto",
            "resolved_by_user_id": actor_id,
            "resolution_motive": cleaned_justification,
            "resolution_conditions": cleaned_conditions,
            "resolved_at": now,
            "project_status": next_project_status,
            "duplicated": False,
            "message": "Evaluación reanudada exitosamente desde el punto de control conservando resultados previos.",
        }

    def get_project_checkpoint(self, project_id: UUID) -> dict[str, Any] | None:
        """Obtiene el punto de control persistente (pendiente o resuelto) para la versión vigente del proyecto (HU3.1 / HU3.4)."""
        project = self.get_project(project_id)
        if project.get("checkpoint"):
            return project["checkpoint"]
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            return RiskCheckpointEngine.get_latest_checkpoint(conn, project["project_version_id"])

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
                    """SELECT e.id AS evaluation_id, e.status, e.project_version_id,
                              o.id AS event_id, o.payload,
                              (o.id IS NOT NULL AND o.published_at IS NULL) AS publication_pending
                       FROM evaluations e
                       LEFT JOIN outbox_events o ON o.aggregate_id=e.id
                       WHERE e.idempotency_key=%s""",
                    (idempotency_key,),
                ).fetchone()
                if previous:
                    previous = dict(previous)
                    previous["duplicated"] = True
                    if previous["status"] == "pending_review":
                        previous["event_id"] = None
                        previous["publication_pending"] = False
                        previous["status_label"] = "Pendiente de revisión"
                        checkpoint = RiskCheckpointEngine.get_active_checkpoint(
                            conn, previous["project_version_id"]
                        )
                        previous["checkpoint"] = checkpoint
                    else:
                        previous["status_label"] = None
                        previous["checkpoint"] = None
                    previous.pop("project_version_id", None)
                    previous.pop("payload", None)
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

                # Comprobar si existe condición de riesgo alto configurada para revisión humana (CA-HU3.1-01)
                risk_info = RiskCheckpointEngine.detect_high_risk_condition(conn, project_version_id)
                if risk_info:
                    evaluation_id = uuid4()
                    conn.execute(
                        """INSERT INTO evaluations
                        (id, project_version_id, criteria_version_id, requested_by_user_id,
                         status, idempotency_key, error_message) VALUES (%s,%s,%s,%s,'pending_review',%s,%s)""",
                        (
                            evaluation_id,
                            project_version_id,
                            snapshot["criteria_version_id"],
                            actor_id,
                            idempotency_key,
                            risk_info["reason"],
                        ),
                    )
                    checkpoint = RiskCheckpointEngine.create_or_get_checkpoint(
                        conn,
                        project_id=snapshot["project_id"],
                        project_version_id=project_version_id,
                        evaluation_id=evaluation_id,
                        risk_info=risk_info,
                    )
                    return {
                        "evaluation_id": evaluation_id,
                        "event_id": None,
                        "status": "pending_review",
                        "status_label": "Pendiente de revisión",
                        "duplicated": False,
                        "publication_pending": False,
                        "checkpoint": checkpoint,
                    }
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
            with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
                conn.execute(
                    "UPDATE outbox_events SET published_at=now(), publish_attempts=publish_attempts+1 WHERE id=%s",
                    (event_id,),
                )
        except Exception:
            publication_pending = True
            with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
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
            "checkpoint": None,
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
            checkpoint = RiskCheckpointEngine.get_active_checkpoint(conn, row["project_version_id"])
            result = None
            if row["status"] != "pending_review" and checkpoint is None and row["economic_assessment_id"]:
                result = {
                    "economic_assessment_id": row["economic_assessment_id"],
                    "cost_per_beneficiary_pen": row["cost_per_beneficiary_pen"],
                    "score_0_100": row["score_0_100"],
                    "explanation": row["explanation"],
                    "algorithm_version": row["algorithm_version"],
                }
            status_label = "Pendiente de revisión" if row["status"] == "pending_review" else (
                "Completada" if row["status"] == "completed" else (
                    "En procesamiento" if row["status"] == "processing" else (
                        "En cola" if row["status"] == "queued" else row["status"]
                    )
                )
            )
            return {
                "evaluation_id": row["evaluation_id"],
                "project_version_id": row["project_version_id"],
                "criteria_version_id": row["criteria_version_id"],
                "status": row["status"],
                "status_label": status_label,
                "checkpoint": checkpoint,
                "result": result,
            }

    def record_legal_abstention(self, project_id: UUID, actor_id: UUID) -> dict[str, Any]:
        """Mantiene compatibilidad con legal_precheck y devuelve el informe jurídico enriquecido con citas (HU2.2)."""
        self.get_project(project_id)
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            conn.execute(
                """INSERT INTO audit_events
                (actor_user_id,action,entity_type,entity_id,details)
                VALUES (%s,'LEGAL_PRECHECK_REQUIRES_REVIEW','project',%s,%s)""",
                (actor_id, project_id, Jsonb({"reason": "legal_assessment_performed"})),
            )
        assessment = self.get_legal_assessment(project_id)
        obs = [
            f"{f['title']}: {f['citation']['limitation_note']}"
            for f in assessment["findings"]
            if not f["citation"]["is_verifiable"]
        ] or [f["description"] for f in assessment["findings"]]
        return {
            "project_id": project_id,
            "status": assessment["status"],
            "complies": False if any(f.get("complies") is False for f in assessment["findings"]) else None,
            "sources": [
                f"{f['citation']['document_name']} ({f['citation']['version']}) - {f['citation']['article_or_section'] or 'Cita no verificable'}"
                for f in assessment["findings"]
            ],
            "requires_review": assessment["requires_human_review"],
            "observations": obs,
            "assessment": assessment,
            "findings": assessment["findings"],
        }

    def evaluate_legal_assessment(
        self,
        project_id: UUID,
        actor_id: UUID,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta y persiste la evaluación jurídica del expediente con citas comprobables (HU2.2/HU2.3)."""
        project = self.get_project(project_id)
        if not _is_db_available(self.db_url):
            raise ServicioNoDisponibleError("Base de datos no disponible")

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            v_row = conn.execute(
                "SELECT id FROM project_versions WHERE project_id = %s ORDER BY version_number DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            version_id = v_row["id"] if v_row else None

            # Aislamiento por versiones: consultar hallazgos de la versión vigente o generales del proyecto
            finding_rows = conn.execute(
                """
                SELECT * FROM project_legal_findings
                WHERE project_id = %s AND (project_version_id = %s OR project_version_id IS NULL)
                ORDER BY created_at ASC
                """,
                (project_id, version_id),
            ).fetchall()

            # Verificar si existe resolución previa de alerta legal para esta versión
            resolution_row = conn.execute(
                """
                SELECT * FROM legal_alert_resolutions
                WHERE project_id = %s AND project_version_id = %s
                ORDER BY resolved_at DESC LIMIT 1
                """,
                (project_id, version_id),
            ).fetchone()

            chunk_ids = [r["normative_chunk_id"] for r in finding_rows if r.get("normative_chunk_id")]
            chunks_by_id: dict[str, dict[str, Any]] = {}
            if chunk_ids:
                chunks = conn.execute(
                    "SELECT * FROM normative_documents WHERE id = ANY(%s)",
                    (chunk_ids,),
                ).fetchall()
                chunks_by_id = {str(c["id"]): dict(c) for c in chunks}

            assessment = LegalAssessmentEngine.evaluate(
                project_id=project_id,
                project_code=project["code"],
                project_version_id=version_id,
                finding_rows=[dict(r) for r in finding_rows],
                chunks_by_id=chunks_by_id,
            )

            # Si existía una resolución formal por Asesoría Jurídica para esta versión, aplicar levantamiento
            if resolution_row and assessment["has_legal_alert"]:
                assessment["has_legal_alert"] = False
                assessment["is_resolved"] = True
                assessment["resolution_justification"] = resolution_row["justification"]

                # HU2.3 Corrección: No marcar como verified sin cambio comprobado en los hallazgos
                all_findings_comply = bool(finding_rows and all(r.get("complies") for r in finding_rows))
                assessment["status"] = (
                    "verified" if (all_findings_comply and assessment["unverifiable_citations_count"] == 0)
                    else "requires_review"
                )
                assessment["status_label"] = (
                    "Alerta Legal Levantada / Citas Verificadas" if assessment["status"] == "verified"
                    else "Alerta Legal Levantada / Requiere revisión de cumplimiento o citas"
                )
                assessment["summary"] += (
                    f" [ALERTA LEVANTADA: {resolution_row['resolution_action']} por Asesor Jurídico. "
                    f"Justificación: {resolution_row['justification']}]"
                )

            assessment_id = UUID(assessment["assessment_id"])
            row_ins = conn.execute(
                """
                INSERT INTO legal_assessments
                (id, project_id, project_code, project_version_id, status, summary, findings_json,
                 total_findings, verifiable_citations_count, unverifiable_citations_count,
                 requires_human_review, has_legal_alert, legal_alert_motive, legal_alert_norm,
                 is_resolved, resolved_by_user_id, resolved_at, resolution_justification, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, project_version_id) DO UPDATE SET
                    project_version_id = EXCLUDED.project_version_id,
                    status = EXCLUDED.status,
                    summary = EXCLUDED.summary,
                    findings_json = EXCLUDED.findings_json,
                    total_findings = EXCLUDED.total_findings,
                    verifiable_citations_count = EXCLUDED.verifiable_citations_count,
                    unverifiable_citations_count = EXCLUDED.unverifiable_citations_count,
                    requires_human_review = EXCLUDED.requires_human_review,
                    has_legal_alert = EXCLUDED.has_legal_alert,
                    legal_alert_motive = EXCLUDED.legal_alert_motive,
                    legal_alert_norm = EXCLUDED.legal_alert_norm,
                    is_resolved = EXCLUDED.is_resolved,
                    resolved_by_user_id = EXCLUDED.resolved_by_user_id,
                    resolved_at = EXCLUDED.resolved_at,
                    resolution_justification = EXCLUDED.resolution_justification,
                    evaluated_at = EXCLUDED.evaluated_at
                RETURNING id
                """,
                (
                    assessment_id,
                    project_id,
                    project["code"],
                    version_id,
                    assessment["status"],
                    assessment["summary"],
                    Jsonb(assessment["findings"]),
                    assessment["total_findings"],
                    assessment["verifiable_citations_count"],
                    assessment["unverifiable_citations_count"],
                    assessment["requires_human_review"],
                    assessment["has_legal_alert"],
                    assessment.get("legal_alert_motive"),
                    assessment.get("legal_alert_norm"),
                    assessment.get("is_resolved", False),
                    resolution_row["resolved_by_user_id"] if resolution_row else None,
                    resolution_row["resolved_at"] if resolution_row else None,
                    assessment.get("resolution_justification"),
                    assessment["evaluated_at"],
                ),
            ).fetchone()
            if row_ins:
                assessment["assessment_id"] = str(row_ins["id"])

            conn.execute(
                """INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'LEGAL_ASSESSMENT_EVALUATED', 'project', %s, %s)""",
                (
                    actor_id,
                    project_id,
                    Jsonb({
                        "project_code": project["code"],
                        "total_findings": assessment["total_findings"],
                        "verifiable_count": assessment["verifiable_citations_count"],
                        "unverifiable_count": assessment["unverifiable_citations_count"],
                        "has_legal_alert": assessment["has_legal_alert"],
                    }),
                ),
            )

            return assessment

    def get_legal_assessment(self, project_id: UUID) -> dict[str, Any]:
        """Recupera la evaluación jurídica del expediente o la evalúa si no existe."""
        project = self.get_project(project_id)
        if not _is_db_available(self.db_url):
            raise ServicioNoDisponibleError("Base de datos no disponible")

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "SELECT * FROM legal_assessments WHERE project_id = %s",
                (project_id,),
            ).fetchone()
            if row:
                current_v_id = project.get("project_version_id")
                # Aislamiento por versiones: si la versión vigente no coincide, reevaluar limpiamente
                if row.get("project_version_id") and current_v_id and row["project_version_id"] != current_v_id:
                    return self.evaluate_legal_assessment(project_id, UUID("10000000-0000-4000-a000-000000000004"))

                status = row["status"]
                if status == "alerta_legal":
                    status_label = "Alerta Legal: Incompatibilidad Normativa/Territorial"
                elif status == "verified":
                    status_label = "Citas normativas verificadas"
                elif status == "insufficient":
                    status_label = "Información jurídica insuficiente"
                else:
                    status_label = "Requiere revisión humana"

                return {
                    "assessment_id": str(row["id"]),
                    "project_id": str(row["project_id"]),
                    "project_code": row["project_code"],
                    "project_version_id": str(row["project_version_id"]) if row.get("project_version_id") else None,
                    "status": status,
                    "status_label": status_label,
                    "summary": row["summary"],
                    "findings": row["findings_json"],
                    "total_findings": row["total_findings"],
                    "verifiable_citations_count": row["verifiable_citations_count"],
                    "unverifiable_citations_count": row["unverifiable_citations_count"],
                    "requires_human_review": row["requires_human_review"],
                    "has_legal_alert": bool(row.get("has_legal_alert", False)),
                    "legal_alert_motive": row.get("legal_alert_motive"),
                    "legal_alert_norm": row.get("legal_alert_norm"),
                    "is_resolved": bool(row.get("is_resolved", False)),
                    "resolution_justification": row.get("resolution_justification"),
                    "evaluated_at": row["evaluated_at"],
                    "is_simulated_corpus": any(
                        isinstance(f, dict) and f.get("citation", {}).get("is_simulated", False)
                        for f in (row["findings_json"] or [])
                    ),
                }

        return self.evaluate_legal_assessment(project_id, UUID("10000000-0000-4000-a000-000000000004"))

    ALLOWED_LEGAL_RESOLUTION_ACTIONS = {
        "falso_positivo",
        "subsanado_en_expediente",
        "excepcion_fundada",
        "riesgo_asumido",
    }

    ACTION_NORMALIZATION = {
        "falso_positivo": "falso_positivo",
        "falso positivo": "falso_positivo",
        "subsanado_en_expediente": "subsanado_en_expediente",
        "subsanado": "subsanado_en_expediente",
        "subsanación": "subsanado_en_expediente",
        "subsanacion": "subsanado_en_expediente",
        "excepcion_fundada": "excepcion_fundada",
        "excepcion": "excepcion_fundada",
        "excepción fundada": "excepcion_fundada",
        "riesgo_asumido": "riesgo_asumido",
        "riesgo normativo asumido": "riesgo_asumido",
    }

    def _verify_legal_resolution_actor(self, actor_id: UUID) -> None:
        """Verifica que el actor tenga rol LEGAL_ADVISOR, ADMIN o SUPERADMIN en auth_db."""
        settings = get_settings()
        auth_dsn = _dsn(settings.auth_db_url)
        with psycopg.connect(auth_dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT r.code
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_id = r.id
                WHERE u.id = %s
                """,
                (actor_id,),
            ).fetchall()
            roles = {r["code"] for r in rows}
            if not (roles & {"LEGAL_ADVISOR", "ADMIN", "SUPERADMIN"}):
                raise AccesoDenegadoError(
                    f"El usuario {actor_id} no cuenta con perfil de Asesor Jurídico o Administrador autorizado. "
                    "Se requiere rol LEGAL_ADVISOR o ADMIN."
                )

    def resolve_legal_alert(
        self,
        project_id: UUID,
        actor_id: UUID,
        resolution_action: str,
        justification: str,
        idempotency_key: str,
        evidence_reference: str | None = None,
    ) -> dict[str, Any]:
        """Permite al Asesor Jurídico o Administrador levantar formalmente una alerta legal activa (HU2.3)."""
        cleaned_key = idempotency_key.strip()
        if not cleaned_key:
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")

        cleaned_action = resolution_action.strip()
        normalized_action = self.ACTION_NORMALIZATION.get(cleaned_action.lower())
        if not normalized_action:
            for k, norm_k in self.ACTION_NORMALIZATION.items():
                if k in cleaned_action.lower():
                    normalized_action = norm_k
                    break
        if not normalized_action:
            raise ConfiguracionPMV1Error(
                f"Acción de resolución '{cleaned_action}' no válida. "
                "Las decisiones permitidas son: 'falso_positivo', 'subsanado_en_expediente', "
                "'excepcion_fundada', 'riesgo_asumido'."
            )

        cleaned_justification = justification.strip()
        if len(cleaned_justification) < 5:
            raise ConfiguracionPMV1Error("La justificación debe tener al menos 5 caracteres")

        cleaned_evidence = evidence_reference.strip() if evidence_reference and evidence_reference.strip() else None

        # HU2.3 Corrección: subsanado_en_expediente exige obligatoriamente referencia probatoria
        if normalized_action == "subsanado_en_expediente":
            if not cleaned_evidence or len(cleaned_evidence) < 5:
                raise ConfiguracionPMV1Error(
                    "La decisión 'subsanado_en_expediente' exige obligatoriamente una referencia documental "
                    "o probatoria ('evidence_reference') con al menos 5 caracteres que sustente la subsanación del expediente."
                )

        # Exigir usuario con rol autorizado
        self._verify_legal_resolution_actor(actor_id)

        project = self.get_project(project_id)
        version_id = project["project_version_id"]

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn, conn.transaction():
            # 1. Comprobación estricta de idempotencia
            prev = conn.execute(
                "SELECT * FROM legal_alert_resolutions WHERE idempotency_key = %s",
                (cleaned_key,),
            ).fetchone()
            if prev:
                if prev["project_id"] != project_id or prev["project_version_id"] != version_id:
                    raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente o versión")
                if (
                    prev["resolution_action"] != normalized_action
                    or prev["justification"] != cleaned_justification
                ):
                    raise ConfiguracionPMV1Error("Idempotency-Key no puede ser reutilizada con datos de resolución distintos")
                return {
                    "resolution_id": prev["id"],
                    "project_id": prev["project_id"],
                    "project_version_id": prev["project_version_id"],
                    "resolved_by_user_id": prev["resolved_by_user_id"],
                    "resolution_action": prev["resolution_action"],
                    "justification": prev["justification"],
                    "evidence_reference": prev.get("evidence_reference"),
                    "resolved_at": prev["resolved_at"],
                    "duplicated": True,
                }

            # 2. Solo permite resolver una alerta activa de la versión vigente.
            current_assessment = conn.execute(
                """
                SELECT id, status, has_legal_alert, is_resolved, summary, unverifiable_citations_count
                FROM legal_assessments
                WHERE project_id = %s AND project_version_id = %s
                """,
                (project_id, version_id),
            ).fetchone()

            if (
                not current_assessment
                or not current_assessment.get("has_legal_alert")
                or current_assessment.get("is_resolved", False)
            ):
                raise ConfiguracionPMV1Error(
                    f"No existe una Alerta Legal activa sin resolver en la versión vigente del expediente. "
                    "Operación rechazada."
                )

            # 3. Registrar la decisión humana POR SEPARADO con usuario, fecha, versión, acción, justificación y evidencia
            resolution_id = uuid4()
            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO legal_alert_resolutions
                (id, project_id, project_version_id, resolved_by_user_id, resolution_action, justification, evidence_reference, resolved_at, idempotency_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    resolution_id,
                    project_id,
                    version_id,
                    actor_id,
                    normalized_action,
                    cleaned_justification,
                    cleaned_evidence,
                    now,
                    cleaned_key,
                ),
            )

            # 4. Conservar hallazgos históricos intactos: NO se muta project_legal_findings a complies=TRUE.

            # 5. Limitar actualización de estado exclusivamente a la versión correcta:
            # HU2.3 Corrección: Una justificación escrita no acredita la subsanación sin una nueva evaluación
            # de los datos corregidos. Levantar la alerta deja el caso en 'requires_review' sin declararlo 'verified'.
            new_status = "requires_review"

            conn.execute(
                """
                UPDATE legal_assessments
                SET status = %s,
                    has_legal_alert = FALSE,
                    is_resolved = TRUE,
                    resolved_by_user_id = %s,
                    resolved_at = %s,
                    resolution_justification = %s,
                    summary = summary || ' [ALERTA LEVANTADA (' || %s || '): ' || %s || ']'
                WHERE project_id = %s AND project_version_id = %s
                """,
                (
                    new_status,
                    actor_id,
                    now,
                    cleaned_justification,
                    normalized_action,
                    cleaned_justification,
                    project_id,
                    version_id,
                ),
            )

            conn.execute(
                """
                INSERT INTO audit_events
                (actor_user_id, action, entity_type, entity_id, details)
                VALUES (%s, 'LEGAL_ALERT_RESOLVED', 'project', %s, %s)
                """,
                (
                    actor_id,
                    project_id,
                    Jsonb({
                        "project_code": project["code"],
                        "resolution_action": normalized_action,
                        "justification": cleaned_justification,
                        "evidence_reference": cleaned_evidence,
                        "project_version_id": str(version_id),
                    }),
                ),
            )

        return {
            "resolution_id": resolution_id,
            "project_id": project_id,
            "project_version_id": version_id,
            "resolved_by_user_id": actor_id,
            "resolution_action": normalized_action,
            "justification": cleaned_justification,
            "evidence_reference": cleaned_evidence,
            "resolved_at": now,
            "duplicated": False,
        }

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
                    if score > 0 and NormativeSearchEngine.is_relevant(
                        item, cleaned_query, keywords
                    ):
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
                if score > 0 and NormativeSearchEngine.is_relevant(
                    item, cleaned_query, keywords
                ):
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

    def get_unified_assessment_summary(
        self, project_id: UUID, version_id: UUID | None = None
    ) -> dict[str, Any]:
        """Genera el resumen unificado de evaluacion multidimensional (HU1.12).

        Cumple estrictamente los criterios de aceptacion:
        - CA-HU1.12-01: Reune los resultados de las cinco dimensiones (economica, social, ambiental,
          tecnica y juridica) en una sola vista con la conclusion y justificacion de la version vigente.
        - CA-HU1.12-02: Expone la puntuacion global consolidada con sus puntuaciones de entrada, pesos
          y formula explicita y reproducible a partir de la version activa de criterios.
        - CA-HU1.12-03: Si alguna dimension sigue pendiente, fallo o carece de datos indispensables,
          identifica la dimension afectada y no presenta una evaluacion incompleta como resultado aprobado.
        - Rigor normativo: Respeta distinciones de datos simulados (HU1.8) y citas no verificables (HU2.2),
          y bloquea aprobacion si existen alertas legales activas (HU2.3) o checkpoints pausados (HU3.1/HU3.4).
        """
        project = self.get_project(project_id)
        current_version_id = version_id or project["project_version_id"]

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            # Obtener datos de la version consultada
            v_row = conn.execute(
                """
                SELECT id, version_number, title, description, location_description,
                       proposed_land_use, estimated_budget_pen, beneficiaries_count
                FROM project_versions
                WHERE id = %s AND project_id = %s
                """,
                (current_version_id, project_id),
            ).fetchone()

            if not v_row:
                raise RecursoPMV1NoEncontradoError("Version del expediente no encontrada")

            version_number = v_row["version_number"]
            dimensions: list[dict[str, Any]] = []
            missing_dimensions: list[str] = []
            blocking_reasons: list[str] = []

            # ---------------------------------------------------------
            # 1. Dimension Economica
            # ---------------------------------------------------------
            econ_row = conn.execute(
                """
                SELECT e.id AS evaluation_id, e.status, e.error_message, e.requested_at,
                       r.cost_per_beneficiary_pen, r.score_0_100, r.explanation, r.algorithm_version
                FROM evaluations e
                LEFT JOIN economic_result_projections r ON r.evaluation_id = e.id
                WHERE e.project_version_id = %s
                ORDER BY e.requested_at DESC
                LIMIT 1
                """,
                (current_version_id,),
            ).fetchone()

            if not econ_row:
                econ_status = "pending"
                econ_label = "Pendiente de evaluacion"
                econ_conclusion = "Evaluacion economica no ejecutada."
                econ_justification = "No se ha solicitado la proyeccion de costo por beneficiario para esta version del expediente."
                econ_score = None
                econ_eval_at = None
                missing_dimensions.append("Economica")
            elif econ_row["status"] == "pending_review":
                econ_status = "blocked"
                econ_label = "Detenido en punto de control"
                econ_conclusion = "Evaluacion economica detenida por riesgo alto en punto de control HITL."
                econ_justification = econ_row.get("error_message") or "Detencion preventiva conforme a HU3.1."
                econ_score = None
                econ_eval_at = econ_row["requested_at"]
                missing_dimensions.append("Economica (Detenida por HITL)")
                blocking_reasons.append("Dimension economica detenida por punto de control de riesgo alto.")
            elif econ_row["status"] == "error":
                econ_status = "failed"
                econ_label = "Evaluacion fallida"
                econ_conclusion = "La evaluacion economica genero un error."
                econ_justification = econ_row.get("error_message") or "Error en calculo de costo por beneficiario."
                econ_score = None
                econ_eval_at = econ_row["requested_at"]
                missing_dimensions.append("Economica (Fallida)")
            else:
                econ_score = float(econ_row["score_0_100"]) if econ_row.get("score_0_100") is not None else None
                cost_pen = econ_row.get("cost_per_beneficiary_pen")
                cost_str = f"S/. {cost_pen:.2f}" if cost_pen is not None else "No determinado"
                econ_status = "completed"
                econ_label = "Completada"
                econ_conclusion = (
                    f"Costo por beneficiario: {cost_str}. Puntuacion normalizada: {econ_score:.1f}/100."
                    if econ_score is not None
                    else f"Costo por beneficiario: {cost_str}."
                )
                econ_justification = econ_row.get("explanation") or "Proyeccion de costo por beneficiario conforme a umbrales vigentes."
                econ_eval_at = econ_row["requested_at"]

            dimensions.append({
                "dimension_code": "economic",
                "dimension_name": "Economica",
                "status": econ_status,
                "status_label": econ_label,
                "conclusion": econ_conclusion,
                "justification": econ_justification,
                "score": econ_score,
                "is_simulated": False,
                "warning": None,
                "has_blocker": (econ_status == "blocked"),
                "blocker_message": "Pausa en punto de control" if econ_status == "blocked" else None,
                "evaluated_at": econ_eval_at,
                "details": {
                    "cost_per_beneficiary_pen": float(econ_row["cost_per_beneficiary_pen"])
                    if econ_row and econ_row.get("cost_per_beneficiary_pen") is not None
                    else None
                },
            })

            # ---------------------------------------------------------
            # 2. Dimension Social
            # ---------------------------------------------------------
            soc_row = conn.execute(
                """
                SELECT id, status, summary, results_json, equity_json, social_score, score_explanation, evaluated_at
                FROM social_accessibility_assessments
                WHERE project_version_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (current_version_id,),
            ).fetchone()

            if not soc_row:
                soc_status = "pending"
                soc_label = "Pendiente de evaluacion"
                soc_conclusion = "Evaluacion de accesibilidad social no ejecutada."
                soc_justification = "No se registran indicadores de proximidad a servicios sociales (salud, educacion, transporte) para esta version."
                soc_score = None
                soc_eval_at = None
                soc_simulated = False
                soc_warning = None
                missing_dimensions.append("Social")
            else:
                soc_score = float(soc_row["social_score"]) if soc_row.get("social_score") is not None else None
                soc_simulated = bool(
                    soc_row.get("results_json")
                    and any(r.get("is_simulated") for r in soc_row["results_json"] if isinstance(r, dict))
                )
                soc_warning = (
                    "Datos de accesibilidad calculados a partir de fuentes simuladas (RENAES/MINEDU)"
                    if soc_simulated
                    else None
                )
                soc_status = "completed" if soc_row["status"] in ("verified", "evaluated", "completed") else "warning"
                soc_label = "Completada" if soc_status == "completed" else "Requiere revision"
                soc_conclusion = soc_row.get("summary") or "Evaluacion social registrada."
                soc_justification = (
                    soc_row.get("score_explanation")
                    or soc_row.get("summary")
                    or "Analisis de cobertura y equidad social territorial."
                )
                soc_eval_at = soc_row["evaluated_at"]

            dimensions.append({
                "dimension_code": "social",
                "dimension_name": "Social",
                "status": soc_status,
                "status_label": soc_label,
                "conclusion": soc_conclusion,
                "justification": soc_justification,
                "score": soc_score,
                "is_simulated": soc_simulated,
                "warning": soc_warning,
                "has_blocker": False,
                "blocker_message": None,
                "evaluated_at": soc_eval_at,
                "details": {"social_score": soc_score},
            })

            # ---------------------------------------------------------
            # 3. Dimension Ambiental
            # ---------------------------------------------------------
            env_row = conn.execute(
                """
                SELECT id, status, risk_level, risk_observation, requires_human_review, favorable,
                       summary, declared_vs_evidence_json, impacts_json, green_area_json, environmental_score, evaluated_at
                FROM environmental_assessments
                WHERE project_version_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (current_version_id,),
            ).fetchone()

            if not env_row:
                env_status = "pending"
                env_label = "Pendiente de evaluacion"
                env_conclusion = "Evaluacion de impacto ambiental territorial no ejecutada."
                env_justification = "No se registran antecedentes ambientales ni verificacion de faja marginal hidrica para esta version."
                env_score = None
                env_eval_at = None
                env_has_blocker = False
                env_blocker_msg = None
                env_simulated = False
                env_warning = None
                missing_dimensions.append("Ambiental")
            else:
                env_score = float(env_row["environmental_score"]) if env_row.get("environmental_score") is not None else None
                risk = env_row.get("risk_level", "low")
                req_rev = env_row.get("requires_human_review", False)
                env_eval_at = env_row["evaluated_at"]

                env_simulated = bool(
                    (env_row.get("declared_vs_evidence_json") and env_row["declared_vs_evidence_json"].get("is_simulated"))
                    or (env_row.get("green_area_json") and env_row["green_area_json"].get("is_simulated"))
                )
                env_warning = "Datos ambientales calculados a partir de capas cartograficas simuladas" if env_simulated else None

                has_pending_cp = RiskCheckpointEngine.has_pending_checkpoint(conn, current_version_id)
                env_has_blocker = (risk == "high" and req_rev and has_pending_cp)

                if risk == "insufficient" or env_row.get("status") == "insufficient":
                    env_status = "failed"
                    env_label = "Informacion insuficiente"
                    env_conclusion = "Informacion ambiental insuficiente para dictaminar."
                    env_justification = env_row.get("risk_observation") or "Faltan datos cartograficos o declarados indispensables."
                    env_blocker_msg = "Datos ambientales indispensables no provistos."
                    missing_dimensions.append("Ambiental (Informacion insuficiente)")
                elif env_has_blocker:
                    env_status = "blocked"
                    env_label = "Alerta de Riesgo Alto (HITL)"
                    env_conclusion = f"Riesgo ambiental territorial ALTO detectado. {env_row.get('summary', '')}"
                    env_justification = env_row.get("risk_observation") or "Requiere autorizacion y levantamiento de pausa en punto de control (HU3.1/HU3.4)."
                    env_blocker_msg = "Riesgo ambiental territorial alto activo sin resolver (HU3.1)."
                    blocking_reasons.append(f"Dimension ambiental con riesgo alto pendiente de revision humana: {env_justification}")
                else:
                    env_status = "completed" if risk in ("low", "moderate") or not has_pending_cp else "warning"
                    env_label = "Completada / Favorable" if env_row.get("favorable") else f"Completada ({risk.capitalize()})"
                    env_conclusion = f"Nivel de riesgo ambiental: {risk.upper()}. {env_row.get('summary', '')}"
                    env_justification = env_row.get("risk_observation") or env_row.get("summary") or "Impactos ambientales y medidas de mitigacion verificados."
                    env_blocker_msg = None

            dimensions.append({
                "dimension_code": "environmental",
                "dimension_name": "Ambiental",
                "status": env_status,
                "status_label": env_label,
                "conclusion": env_conclusion,
                "justification": env_justification,
                "score": env_score,
                "is_simulated": env_simulated,
                "warning": env_warning,
                "has_blocker": env_has_blocker,
                "blocker_message": env_blocker_msg,
                "evaluated_at": env_eval_at,
                "details": {"risk_level": env_row.get("risk_level") if env_row else None},
            })

            # ---------------------------------------------------------
            # 4. Dimension Tecnica (HU1.8)
            # ---------------------------------------------------------
            tech_row = conn.execute(
                """
                SELECT id, status, overall_result, overall_result_label, is_viable,
                       technical_score, score_explanation, dimension_conclusion, dimension_justification,
                       findings_json, criteria_summary, evaluated_at
                FROM technical_feasibility_assessments
                WHERE project_version_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (current_version_id,),
            ).fetchone()

            if not tech_row:
                tech_status = "pending"
                tech_label = "Pendiente de evaluacion"
                tech_conclusion = "Evaluacion de viabilidad tecnica no ejecutada."
                tech_justification = "No se ha procesado el analisis de diseno geometrico, pendientes ni capacidad portante (HU1.8)."
                tech_score = None
                tech_eval_at = None
                tech_simulated = False
                tech_warning = None
                missing_dimensions.append("Tecnica")
            else:
                tech_score = float(tech_row["technical_score"]) if tech_row.get("technical_score") is not None else None
                tech_simulated = bool(
                    tech_row.get("findings_json")
                    and any(c.get("is_simulated") for c in tech_row["findings_json"] if isinstance(c, dict))
                )
                tech_warning = (
                    "Datos de viabilidad calculados a partir de expediente tecnico simulado (HU1.8); requiere verificacion en campo."
                    if tech_simulated
                    else None
                )
                if tech_row["overall_result"] == "cumple":
                    tech_status = "completed"
                    tech_label = "Viable (Cumple)"
                elif tech_row["overall_result"] == "observado":
                    tech_status = "warning"
                    tech_label = "Observado"
                elif tech_row["overall_result"] == "informacion_insuficiente":
                    tech_status = "failed"
                    tech_label = "Informacion insuficiente"
                    missing_dimensions.append("Tecnica (Informacion insuficiente)")
                else:
                    tech_status = "failed"
                    tech_label = tech_row.get("overall_result_label") or "No viable"
                    missing_dimensions.append(f"Tecnica ({tech_label})")

                tech_conclusion = tech_row["dimension_conclusion"]
                tech_justification = tech_row["dimension_justification"]
                tech_eval_at = tech_row["evaluated_at"]

            dimensions.append({
                "dimension_code": "technical",
                "dimension_name": "Tecnica",
                "status": tech_status,
                "status_label": tech_label,
                "conclusion": tech_conclusion,
                "justification": tech_justification,
                "score": tech_score,
                "is_simulated": tech_simulated,
                "warning": tech_warning,
                "has_blocker": (tech_status == "failed"),
                "blocker_message": "Viabilidad tecnica observada o no cumplida" if tech_status == "failed" else None,
                "evaluated_at": tech_eval_at,
                "details": {"technical_score": tech_score},
            })

            # ---------------------------------------------------------
            # 5. Dimension Juridica (HU2.2 & HU2.3)
            # ---------------------------------------------------------
            legal_row = conn.execute(
                """
                SELECT id, status, summary, verifiable_citations_count, unverifiable_citations_count,
                       requires_human_review, has_legal_alert, legal_alert_motive, legal_alert_norm,
                       is_resolved, resolution_justification, evaluated_at, findings_json
                FROM legal_assessments
                WHERE project_id = %s AND project_version_id = %s
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (project_id, current_version_id),
            ).fetchone()

            if not legal_row:
                legal_status = "pending"
                legal_label = "Pendiente de evaluacion"
                legal_conclusion = "Evaluacion juridica y contraste normativo no ejecutada."
                legal_justification = "No se ha emitido dictamen normativo ni cotejo de citas juridicas para esta version."
                legal_eval_at = None
                legal_has_blocker = False
                legal_blocker_msg = None
                legal_warning = None
                missing_dimensions.append("Juridica")
            else:
                has_active_alert = bool(
                    (legal_row["status"] == "alerta_legal" or legal_row.get("has_legal_alert"))
                    and not legal_row.get("is_resolved", False)
                )
                unverifiable = legal_row.get("unverifiable_citations_count", 0)
                legal_eval_at = legal_row["evaluated_at"]
                legal_warning = None

                if has_active_alert:
                    legal_status = "blocked"
                    legal_label = "Alerta Legal Activa"
                    motive = legal_row.get("legal_alert_motive") or "Incompatibilidad territorial"
                    norm = legal_row.get("legal_alert_norm") or "Plan urbano"
                    legal_conclusion = f"ALERTA LEGAL (HU2.3): Incompatibilidad normativa/territorial con {norm}."
                    legal_justification = f"Motivo: {motive}. Conforme a HU2.3, se bloquea la aprobacion y priorizacion definitiva."
                    legal_has_blocker = True
                    legal_blocker_msg = f"Alerta Legal activa: {motive} [{norm}]."
                    blocking_reasons.append(f"Dimension juridica con Alerta Legal activa sin resolver (HU2.3): {motive}")
                elif unverifiable > 0 or legal_row.get("requires_human_review") or legal_row.get("status") == "requires_review":
                    legal_status = "warning"
                    legal_label = "Requiere revision humana"
                    legal_conclusion = legal_row.get("summary") or "Revision juridica con citas no comprobables o dictamen pendiente."
                    legal_justification = (
                        f"Se detectaron {unverifiable} cita(s) no verificable(s) (HU2.2); requiere cotejo manual por el Asesor Juridico."
                        if unverifiable > 0
                        else "Evaluacion juridica en estado 'requires_review' pendiente de subsanacion o dictamen formal."
                    )
                    legal_has_blocker = True
                    legal_blocker_msg = "Dimension juridica requiere revision humana formal (HU2.2/HU1.12)."
                    legal_warning = "Contiene citas no comprobables contra normativa oficial o dictamen pendiente."
                    missing_dimensions.append("Juridica (Requiere revision humana)")
                    blocking_reasons.append("Dimension juridica en estado 'requires_review' por citas normativas no verificables o dictamen legal pendiente (HU2.2/HU1.12).")
                else:
                    legal_status = "completed"
                    legal_label = "Citas normativas verificadas"
                    legal_conclusion = legal_row.get("summary") or "Citas juridicas verificadas."
                    legal_justification = f"Todas las citas ({legal_row.get('verifiable_citations_count', 0)}) fueron debidamente cotejadas contra el corpus normativo vigente."
                    legal_has_blocker = False
                    legal_blocker_msg = None
                    legal_warning = None

            dimensions.append({
                "dimension_code": "legal",
                "dimension_name": "Juridica",
                "status": legal_status,
                "status_label": legal_label,
                "conclusion": legal_conclusion,
                "justification": legal_justification,
                "score": None,  # Dimension juridica es cualitativa y de control normativo
                "is_simulated": False,
                "warning": legal_warning,
                "has_blocker": legal_has_blocker,
                "blocker_message": legal_blocker_msg,
                "evaluated_at": legal_eval_at,
                "details": {
                    "verifiable_citations_count": legal_row.get("verifiable_citations_count", 0) if legal_row else 0,
                    "unverifiable_citations_count": legal_row.get("unverifiable_citations_count", 0) if legal_row else 0,
                },
            })

            # ---------------------------------------------------------
            # 6. Puntuacion Global Explicable (CA-HU1.12-02 & CA-HU1.12-03)
            # ---------------------------------------------------------
            crit_row = conn.execute(
                """
                SELECT id, version_number FROM criteria_versions
                WHERE status = 'active'
                ORDER BY activated_at DESC LIMIT 1
                """
            ).fetchone()

            crit_weights_rows = []
            if crit_row:
                crit_weights_rows = conn.execute(
                    """
                    SELECT criterion_code, weight_percent
                    FROM criterion_weights
                    WHERE criteria_version_id = %s
                    ORDER BY criterion_code ASC
                    """,
                    (crit_row["id"],),
                ).fetchall()

            raw_weights = {r["criterion_code"]: float(r["weight_percent"]) for r in crit_weights_rows}

            # Normalizar codigos de criterios soportados
            def _norm_code(c: str) -> str:
                cu = c.upper().strip()
                if cu in ("ECONOMIC", "ECONOMICA", "ECONOMICO"):
                    return "ECONOMIC"
                if cu in ("SOCIAL", "SOCIALES"):
                    return "SOCIAL"
                if cu in ("ENVIRONMENTAL", "AMBIENTAL", "MEDIOAMBIENTAL"):
                    return "ENVIRONMENTAL"
                if cu in ("TECHNICAL", "TECNICA", "TECNICO"):
                    return "TECHNICAL"
                return cu

            weights_dict = {_norm_code(k): v for k, v in raw_weights.items()}

            input_scores_dict: dict[str, float] = {}
            if econ_score is not None:
                input_scores_dict["ECONOMIC"] = round(econ_score, 2)
            if soc_score is not None:
                input_scores_dict["SOCIAL"] = round(soc_score, 2)
            if env_score is not None:
                input_scores_dict["ENVIRONMENTAL"] = round(env_score, 2)
            if tech_score is not None:
                input_scores_dict["TECHNICAL"] = round(tech_score, 2)

            is_complete = (len(missing_dimensions) == 0)

            global_score_val = None
            is_score_calculated = False
            formula_text = ""
            explanation_text = ""

            if not crit_row or not weights_dict:
                formula_text = "No existe una version activa de criterios y pesos normativos configurada."
                explanation_text = "No se puede calcular puntuacion global explicable sin ponderaciones activas."
            elif not is_complete:
                missing_str = ", ".join(missing_dimensions)
                formula_text = f"Puntuacion no calculable: faltan dimensiones indispensables ({missing_str})."
                explanation_text = (
                    f"Conforme a CA-HU1.12-03, una evaluacion parcial no produce puntuacion global definitiva. "
                    f"Dimensiones pendientes o no viables: {missing_str}."
                )
            else:
                unscored_criteria = [
                    code for code in weights_dict
                    if code in ("ECONOMIC", "SOCIAL", "ENVIRONMENTAL", "TECHNICAL") and code not in input_scores_dict
                ]
                if unscored_criteria:
                    formula_text = f"Puntuacion no calculable: faltan puntuaciones cuantitativas para criterios ponderados ({', '.join(unscored_criteria)})."
                    explanation_text = "Se requiere registrar puntuacion valida para todos los criterios con peso asignado."
                else:
                    weighted_sum = sum(
                        input_scores_dict[code] * (weights_dict[code] / 100.0)
                        for code in weights_dict if code in input_scores_dict
                    )
                    total_weight = sum(weights_dict[code] for code in weights_dict if code in input_scores_dict)
                    if total_weight > 0:
                        calc_score = round(weighted_sum * (100.0 / total_weight), 2)
                        global_score_val = calc_score
                        is_score_calculated = True

                        terms = [
                            f"[{code}: {input_scores_dict[code]:.1f} * {weights_dict[code]:.1f}%]"
                            for code in weights_dict if code in input_scores_dict
                        ]
                        formula_text = f"({' + '.join(terms)}) / {total_weight:.1f}% = {calc_score:.2f} pts"
                        explanation_text = (
                            f"Puntuacion global consolidada calculada a partir de la version activa de criterios v{crit_row['version_number']}. "
                            f"Ponderacion aplicada sobre {len(terms)} criterio(s) cuantitativo(s)."
                        )

            has_blockers = (len(blocking_reasons) > 0)
            if has_blockers:
                summary_status = "blocked"
                summary_status_label = "Bloqueado por alertas o punto de control"
            elif not is_complete:
                summary_status = "incomplete"
                summary_status_label = "Evaluacion multidimensional incompleta"
            else:
                summary_status = "completed"
                summary_status_label = "Evaluacion multidimensional completa"

            allows_final_approval = (is_complete and not has_blockers)

            resumen_parts = [
                f"Expediente {project['code']} (version {version_number}): "
                f"Dimensiones finalizadas: {5 - len(missing_dimensions)}/5."
            ]
            if global_score_val is not None:
                resumen_parts.append(f"Puntuacion consolidada: {global_score_val:.2f}/100.")
            if has_blockers:
                resumen_parts.append(f"Requiere resolver: {'; '.join(blocking_reasons)}.")
            elif not is_complete:
                resumen_parts.append(f"Pendiente de completar: {', '.join(missing_dimensions)}.")
            else:
                resumen_parts.append("Expediente con evaluacion completa y expedita para dictamen humano formal.")

            summary_text = " ".join(resumen_parts)

            return {
                "project_id": project_id,
                "project_code": project["code"],
                "project_version_id": current_version_id,
                "version_number": version_number,
                "is_complete": is_complete,
                "status": summary_status,
                "status_label": summary_status_label,
                "summary_text": summary_text,
                "dimensions": dimensions,
                "missing_dimensions": missing_dimensions,
                "global_score": {
                    "score": global_score_val,
                    "is_calculated": is_score_calculated,
                    "formula": formula_text,
                    "criteria_version_id": crit_row["id"] if crit_row else None,
                    "criteria_version_number": crit_row["version_number"] if crit_row else None,
                    "weights": weights_dict,
                    "input_scores": input_scores_dict,
                    "explanation": explanation_text,
                },
                "allows_final_approval": allows_final_approval,
                "blocking_reasons": blocking_reasons,
                "generated_at": datetime.now(timezone.utc),
            }

    def verify_prioritization_allowed(self, project_id: UUID) -> dict[str, Any]:
        """Control de precondiciones para la futura priorización definitiva (HU2.3 / HU3.1 / HU1.12).

        Verifica que el expediente no tenga Alerta Legal activa sin resolver,
        que no tenga puntos de control (checkpoints) en pausa/revisión humana pendiente,
        y que se encuentre debidamente evaluado.
        """
        project = self.get_project(project_id)
        version_id = project["project_version_id"]
        blocking_reasons: list[str] = []

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            # 1. Control HU2.3: Alerta Legal activa
            legal_row = conn.execute(
                """
                SELECT status, has_legal_alert, legal_alert_motive, legal_alert_norm, is_resolved
                FROM legal_assessments
                WHERE project_id = %s AND project_version_id = %s
                ORDER BY evaluated_at DESC LIMIT 1
                """,
                (project_id, version_id),
            ).fetchone()
            if legal_row and (legal_row["status"] == "alerta_legal" or legal_row.get("has_legal_alert")) and not legal_row.get("is_resolved", False):
                motive = legal_row.get("legal_alert_motive") or "Incompatibilidad territorial o normativa"
                norm = legal_row.get("legal_alert_norm") or "Normativa territorial"
                blocking_reasons.append(
                    f"Alerta Legal activa por incompatibilidad territorial/normativa (HU2.3): {motive} [{norm}]. "
                    "Se requiere resolución formal de Asesoría Jurídica antes de la priorización definitiva."
                )

            # 2. Control HU3.1 / HU3.4: Checkpoint HITL pendiente
            if RiskCheckpointEngine.has_pending_checkpoint(conn, version_id):
                active_cp = RiskCheckpointEngine.get_active_checkpoint(conn, version_id)
                reason = active_cp["reason"] if active_cp else "Punto de control de riesgo alto activo"
                blocking_reasons.append(
                    f"Punto de control de riesgo alto en estado 'Pendiente de revisión' (HU3.1/HU3.4): {reason}. "
                    "Se requiere autorización y reanudación por Gerencia antes de la priorización definitiva."
                )

        allows_prioritization = len(blocking_reasons) == 0
        return {
            "project_id": str(project_id),
            "project_version_id": str(version_id),
            "project_code": project["code"],
            "allows_prioritization": allows_prioritization,
            "blocking_reasons": blocking_reasons,
        }

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
        if project["status"] == "pending_review" or project.get("checkpoint") is not None:
            raise ConfiguracionPMV1Error(
                "El expediente se encuentra en estado 'Pendiente de revisión' en su versión vigente. "
                "Conforme a HU3.1, no se puede emitir una aprobación final mientras la revisión humana esté pendiente."
            )

        if cleaned_decision == "approved":
            unified_summary = self.get_unified_assessment_summary(
                project_id=project_id,
                version_id=project["project_version_id"],
            )
            if not unified_summary["allows_final_approval"]:
                reasons = unified_summary.get("blocking_reasons") or [
                    "La evaluación multidimensional está incompleta o contiene dimensiones no conformes."
                ]
                raise ConfiguracionPMV1Error(
                    "Aprobación final bloqueada por el resumen unificado (HU1.12): "
                    + " ".join(str(reason) for reason in reasons)
                )

        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            if RiskCheckpointEngine.has_pending_checkpoint(conn, project["project_version_id"]):
                raise ConfiguracionPMV1Error(
                    "El expediente se encuentra en estado 'Pendiente de revisión' por punto de control de riesgo alto en su versión vigente. "
                    "Conforme a HU3.1, no se puede emitir una aprobación final mientras la revisión humana esté pendiente."
                )

            # HU2.3: Bloqueo de aprobación definitiva si existe Alerta Legal activa en la versión vigente
            legal_row = conn.execute(
                """
                SELECT status, has_legal_alert, legal_alert_motive, legal_alert_norm, is_resolved
                FROM legal_assessments
                WHERE project_id = %s AND (project_version_id = %s OR project_version_id IS NULL)
                """,
                (project_id, project["project_version_id"]),
            ).fetchone()
            if legal_row and (legal_row["status"] == "alerta_legal" or legal_row.get("has_legal_alert")) and not legal_row.get("is_resolved", False):
                if cleaned_decision == "approved":
                    motive = legal_row.get("legal_alert_motive") or "Incompatibilidad territorial o normativa"
                    norm = legal_row.get("legal_alert_norm") or "Normativa territorial"
                    raise ConfiguracionPMV1Error(
                        f"Aprobación final y priorización bloqueadas por Alerta Legal activa (HU2.3): "
                        f"{motive} [{norm}]. "
                        "El expediente no puede avanzar a aprobación definitiva ni a priorización hasta que la alerta sea resuelta o levantada por Asesoría Jurídica."
                    )

            # HU1.12 / HU2.2: Bloqueo si la dimensión jurídica está en requires_review (citas no verificables o dictamen pendiente)
            if legal_row and legal_row["status"] == "requires_review":
                if cleaned_decision == "approved":
                    raise ConfiguracionPMV1Error(
                        "Aprobación final bloqueada: la dimensión jurídica se encuentra en estado 'requires_review' "
                        "debido a citas normativas no verificables o dictamen legal pendiente (HU2.2/HU1.12). "
                        "Conforme a CA-HU1.12-03, una evaluación incompleta o en revisión no puede habilitar la aprobación definitiva."
                    )

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
        checkpoint = project.get("checkpoint")
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            if not checkpoint:
                checkpoint = RiskCheckpointEngine.get_active_checkpoint(conn, project["project_version_id"])
            latest = conn.execute(
                """
                SELECT id AS approval_id, project_id, project_version_id, decision,
                       justification, conditions, decided_by_user_id, idempotency_key, decided_at
                FROM human_approvals
                WHERE project_id = %s AND project_version_id = %s
                ORDER BY decided_at DESC
                LIMIT 1
                """,
                (project_id, project["project_version_id"]),
            ).fetchone()

        legal_row = None
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            legal_row = conn.execute(
                """
                SELECT status, has_legal_alert, legal_alert_motive, legal_alert_norm, is_resolved
                FROM legal_assessments
                WHERE project_id = %s AND (project_version_id = %s OR project_version_id IS NULL)
                """,
                (project_id, project["project_version_id"]),
            ).fetchone()

        has_legal_alert = bool(
            legal_row and (legal_row["status"] == "alerta_legal" or legal_row.get("has_legal_alert"))
            and not legal_row.get("is_resolved", False)
        )
        legal_alert_motive = legal_row.get("legal_alert_motive") if has_legal_alert else None
        legal_alert_norm = legal_row.get("legal_alert_norm") if has_legal_alert else None

        # HU1.12 / HU2.2: Una dimensión jurídica en 'requires_review' bloquea la aprobación final
        legal_requires_review = bool(
            legal_row and legal_row["status"] == "requires_review" and not has_legal_alert
        )

        unified_summary = self.get_unified_assessment_summary(
            project_id=project_id,
            version_id=project["project_version_id"],
        )

        is_paused = (checkpoint is not None) or (project["status"] == "pending_review")
        is_evaluated = project["status"] in ("evaluated", "approved", "rejected", "observed") and not is_paused

        blocking_reasons: list[str] = []
        if is_paused:
            blocking_reasons.append(checkpoint["reason"] if checkpoint else "Expediente detenido en punto de control por riesgo alto")
        if has_legal_alert:
            blocking_reasons.append(f"Alerta Legal activa (HU2.3): {legal_alert_motive} [{legal_alert_norm}]")
        if legal_requires_review:
            blocking_reasons.append("Dimensión jurídica en estado 'requires_review' por citas no verificables o dictamen pendiente (HU2.2/HU1.12)")

        for reason in unified_summary.get("blocking_reasons", []):
            if reason not in blocking_reasons:
                blocking_reasons.append(reason)

        allows_final_approval = (
            not is_paused
            and not has_legal_alert
            and not legal_requires_review
            and bool(unified_summary.get("allows_final_approval"))
        )
        requires_human_approval = project["status"] == "evaluated" and latest is None and allows_final_approval

        return {
            "project_id": project_id,
            "project_version_id": project["project_version_id"],
            "project_status": project["status"],
            "is_evaluated": is_evaluated,
            "requires_human_approval": requires_human_approval,
            "is_paused": is_paused,
            "pause_reason": checkpoint["reason"] if checkpoint else None,
            "checkpoint": checkpoint,
            "current_approval": dict(latest) if latest else None,
            "has_legal_alert": has_legal_alert,
            "legal_alert_motive": legal_alert_motive,
            "legal_alert_norm": legal_alert_norm,
            "allows_final_approval": allows_final_approval,
            "blocking_reasons": blocking_reasons,
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

            pv_id = project.get("project_version_id")
            ver_num = project.get("version_number", 1)

            rows = conn.execute(
                """
                SELECT id, project_id, project_version_id, project_code, has_sufficient_data,
                       environmental_component, declared_impacts, declared_measures,
                       verifiable_evidence, proximity_to_water_meters,
                       is_in_protected_or_risk_area, source_name, data_origin, description
                FROM project_environmental_records
                WHERE project_version_id = %s
                ORDER BY created_at ASC
                """,
                (pv_id,),
            ).fetchall()
            if not rows and ver_num == 1:
                rows = conn.execute(
                    """
                    SELECT id, project_id, project_version_id, project_code, has_sufficient_data,
                           environmental_component, declared_impacts, declared_measures,
                           verifiable_evidence, proximity_to_water_meters,
                           is_in_protected_or_risk_area, source_name, data_origin, description
                    FROM project_environmental_records
                    WHERE (project_id = %s OR project_code = %s) AND project_version_id IS NULL
                    ORDER BY created_at ASC
                    """,
                    (project_id, project["code"]),
                ).fetchall()

            green_rows = conn.execute(
                """
                SELECT id, project_id, project_version_id, project_code, has_sufficient_data,
                       total_project_area_m2, green_area_m2, green_area_percentage,
                       delimitation_description, declared_affectation, verifiable_affectation,
                       affectation_type, protection_measures, has_sufficient_measures,
                       score_effect_pts, effect_type, calculation_explanation,
                       source_name, data_origin, description,
                       (data_origin = 'simulated') AS is_simulated
                FROM project_green_area_records
                WHERE project_version_id = %s
                ORDER BY created_at ASC
                """,
                (pv_id,),
            ).fetchall()
            if not green_rows and ver_num == 1:
                green_rows = conn.execute(
                    """
                    SELECT id, project_id, project_version_id, project_code, has_sufficient_data,
                           total_project_area_m2, green_area_m2, green_area_percentage,
                           delimitation_description, declared_affectation, verifiable_affectation,
                           affectation_type, protection_measures, has_sufficient_measures,
                           score_effect_pts, effect_type, calculation_explanation,
                           source_name, data_origin, description,
                           (data_origin = 'simulated') AS is_simulated
                    FROM project_green_area_records
                    WHERE (project_id = %s OR project_code = %s) AND project_version_id IS NULL
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

            checkpoint = None
            if (
                assessment.get("risk_level") == "high"
                and assessment.get("requires_human_review")
            ):
                # HU3.1: el hallazgo ambiental debe detener el flujo en el mismo
                # acto que lo registra. Esperar a una solicitud económica posterior
                # dejaba disponibles otras etapas y no constituía una pausa real.
                risk_info = RiskCheckpointEngine.detect_high_risk_condition(
                    conn, project["project_version_id"]
                )
                if risk_info:
                    checkpoint = RiskCheckpointEngine.create_or_get_checkpoint(
                        conn,
                        project_id=project_id,
                        project_version_id=project["project_version_id"],
                        evaluation_id=None,
                        risk_info=risk_info,
                    )

        return {
            **assessment,
            "checkpoint": checkpoint,
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
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.transaction():
                inserted = conn.execute(
                    "INSERT INTO inbox_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING event_id",
                    (event_id,),
                ).fetchone()
                if not inserted:
                    return

                ev_row = conn.execute(
                    """SELECT e.id, e.status, e.project_version_id, pv.project_id
                    FROM evaluations e
                    JOIN project_versions pv ON pv.id = e.project_version_id
                    WHERE e.id = %s""",
                    (evaluation_id,),
                ).fetchone()

                if not ev_row:
                    return

                project_id = ev_row["project_id"]
                project_version_id = ev_row["project_version_id"]

                # Comprobar si la evaluación ya está en pausa o si existe o surge una condición de riesgo alto
                is_already_paused = (ev_row["status"] == "pending_review")
                existing_checkpoint = RiskCheckpointEngine.get_active_checkpoint(conn, project_version_id)
                risk_info = RiskCheckpointEngine.detect_high_risk_condition(conn, project_version_id)

                if is_already_paused or existing_checkpoint or risk_info:
                    if not existing_checkpoint and risk_info:
                        RiskCheckpointEngine.create_or_get_checkpoint(
                            conn,
                            project_id=project_id,
                            project_version_id=project_version_id,
                            evaluation_id=evaluation_id,
                            risk_info=risk_info,
                        )
                    conn.execute(
                        "UPDATE evaluations SET status='pending_review' WHERE id=%s",
                        (evaluation_id,),
                    )
                    conn.execute(
                        "UPDATE projects SET status='pending_review', updated_at=now() WHERE id=%s",
                        (project_id,),
                    )
                    # Detención estricta: NO insertar en economic_result_projections para evaluaciones pausadas
                    return

                # CA-HU3.1-02: Continuación cuando no hay riesgo alto
                conn.execute(
                    """INSERT INTO economic_result_projections
                    (evaluation_id,economic_assessment_id,cost_per_beneficiary_pen,score_0_100,
                     explanation,algorithm_version) VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (evaluation_id) DO UPDATE SET
                        economic_assessment_id = EXCLUDED.economic_assessment_id,
                        cost_per_beneficiary_pen = EXCLUDED.cost_per_beneficiary_pen,
                        score_0_100 = EXCLUDED.score_0_100,
                        explanation = EXCLUDED.explanation,
                        algorithm_version = EXCLUDED.algorithm_version""",
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
                    "UPDATE projects SET status='evaluated',updated_at=now() WHERE id=%s",
                    (project_id,),
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
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
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
