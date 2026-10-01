"""Simula el flujo de la seccion 6 del modelo, sin backend, para probar la base de datos.

ms-platform: crea evaluacion + outbox (una transaccion) -> publica
ms-economic: recibe la instantanea, calcula y guarda (su propia transaccion, idempotente)
ms-platform: recibe el resultado con inbox, guarda la proyeccion y la auditoria

Uso:
    python database/simular_flujo.py              evalua los proyectos A y B
    python database/simular_flujo.py --duplicar   reenvia los mismos eventos (prueba de idempotencia)
"""
import json
import sys
import uuid
from decimal import ROUND_HALF_UP, Decimal

from psycopg.types.json import Jsonb

from _comun import conectar

NS = uuid.UUID("5a1b2c3d-0000-4000-a000-000000000000")   # UUID deterministas para poder repetir
PLANNER = "10000000-0000-4000-a000-000000000002"
ALGORITMO = "economic-cost-per-beneficiary-v1"
DOS = Decimal("0.01")


def u(*partes) -> str:
    return str(uuid.uuid5(NS, ":".join(map(str, partes))))


# ---------------- ms-platform: pasos 3 y 4 ----------------
def solicitar(plat) -> None:
    criterio = plat.execute(
        "SELECT id, excellent_cost_pen, unacceptable_cost_pen FROM criteria_versions WHERE status = 'active'").fetchone()
    if criterio is None:
        sys.exit("No hay politica de criterios activa")
    cv, exc, inac = criterio
    versiones = plat.execute("""
        SELECT DISTINCT ON (pv.project_id) pv.id, pv.estimated_budget_pen, pv.beneficiaries_count, p.code
        FROM project_versions pv JOIN projects p ON p.id = pv.project_id
        WHERE p.code IN ('PRY-A','PRY-B') ORDER BY pv.project_id, pv.version_number DESC""").fetchall()
    for pv, budget, benef, code in versiones:
        ev, event = u("evaluation", pv, cv), u("requested", pv, cv)
        with plat.transaction():
            fila = plat.execute("""
                INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key)
                VALUES (%s, %s, %s, %s, %s) ON CONFLICT (idempotency_key) DO NOTHING RETURNING id""",
                (ev, pv, cv, PLANNER, f"eval:{pv}:{cv}")).fetchone()
            if fila is None:
                print(f"  {code}: la evaluacion ya existia (idempotency_key), no se duplica")
                continue
            payload = {"schema_version": 1, "event_id": event, "event_type": "EconomicEvaluationRequested",
                       "evaluation_id": ev, "project_version_id": str(pv), "criteria_version_id": str(cv),
                       "budget_pen": str(budget), "beneficiaries_count": benef,
                       "excellent_cost_pen": str(exc), "unacceptable_cost_pen": str(inac)}
            plat.execute("INSERT INTO outbox_events (id, event_type, aggregate_id, payload) VALUES (%s,%s,%s,%s)",
                         (event, "EconomicEvaluationRequested", ev, Jsonb(payload)))
            plat.execute("UPDATE projects SET status='evaluating', updated_at=now() WHERE code=%s", (code,))
            plat.execute("""INSERT INTO audit_events (actor_user_id, action, entity_type, entity_id, details)
                            VALUES (%s,'EVALUATION_REQUESTED','evaluation',%s,%s)""", (PLANNER, ev, Jsonb({"project": code})))
            print(f"  {code}: evaluacion {ev[:8]} en cola + evento en outbox")


def publicar(plat, duplicar: bool) -> list[dict]:
    if duplicar:   # reenvio deliberado de eventos ya publicados
        filas = plat.execute("SELECT payload FROM outbox_events WHERE event_type='EconomicEvaluationRequested'").fetchall()
        return [f[0] for f in filas]
    with plat.transaction():
        filas = plat.execute("""SELECT id, payload FROM outbox_events WHERE published_at IS NULL
                                AND event_type='EconomicEvaluationRequested' ORDER BY created_at FOR UPDATE""").fetchall()
        for oid, _ in filas:
            plat.execute("UPDATE outbox_events SET published_at=now(), publish_attempts=publish_attempts+1 WHERE id=%s", (oid,))
    print(f"  publicados {len(filas)} eventos al broker (simulado)")
    return [f[1] for f in filas]


# ---------------- ms-economic: pasos 5 y 6 ----------------
def evaluar_economico(eco, msg: dict) -> dict:
    existente = eco.execute("""SELECT a.id, a.cost_per_beneficiary_pen, a.score_0_100, a.explanation
        FROM processed_requests r JOIN economic_assessments a ON a.id = r.assessment_id
        WHERE r.event_id=%s OR r.evaluation_id=%s""", (msg["event_id"], msg["evaluation_id"])).fetchone()
    if existente:
        aid, costo, puntos, expl = existente
        print(f"  ms-economic: evento repetido -> devuelve el resultado existente {str(aid)[:8]}")
    else:
        budget, benef = Decimal(msg["budget_pen"]), msg["beneficiaries_count"]
        exc, inac = Decimal(msg["excellent_cost_pen"]), Decimal(msg["unacceptable_cost_pen"])
        if budget <= 0 or benef <= 0 or not (0 < exc < inac):
            raise ValueError("Entradas invalidas: no se genera puntuacion")
        costo_exacto = budget / benef
        if costo_exacto <= exc:
            bruto = Decimal(100)
        elif costo_exacto >= inac:
            bruto = Decimal(0)
        else:
            bruto = 100 * (inac - costo_exacto) / (inac - exc)
        puntos = min(max(bruto, Decimal(0)), Decimal(100)).quantize(DOS, ROUND_HALF_UP)
        costo = costo_exacto.quantize(DOS, ROUND_HALF_UP)
        expl = (f"Costo por beneficiario = S/ {budget} / {benef} = S/ {costo}. Con excelente S/ {exc} e inaceptable "
                f"S/ {inac}, puntuacion = {puntos}. Indicador didactico: no mide retorno social ni viabilidad.")
        aid = u("assessment", msg["evaluation_id"])
        with eco.transaction():
            eco.execute("""INSERT INTO economic_assessments (id, evaluation_id, project_version_id, criteria_version_id,
                budget_snapshot_pen, beneficiaries_snapshot, excellent_cost_snapshot_pen, unacceptable_cost_snapshot_pen,
                cost_per_beneficiary_pen, score_0_100, explanation, algorithm_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (aid, msg["evaluation_id"], msg["project_version_id"], msg["criteria_version_id"],
                 budget, benef, exc, inac, costo, puntos, expl, ALGORITMO))
            for code, valor, unidad, formula in [
                    ("COST_PER_BENEFICIARY", costo_exacto, "PEN/persona", "budget / beneficiaries"),
                    ("ECONOMIC_SCORE", bruto, "puntos 0-100", "100*(inaceptable-costo)/(inaceptable-excelente), limitado a 0-100")]:
                eco.execute("""INSERT INTO assessment_metrics (id, assessment_id, metric_code, numeric_value, unit, formula)
                               VALUES (%s,%s,%s,%s,%s,%s)""", (u("metric", aid, code), aid, code, valor, unidad, formula))
            eco.execute("INSERT INTO processed_requests (event_id, evaluation_id, assessment_id) VALUES (%s,%s,%s)",
                        (msg["event_id"], msg["evaluation_id"], aid))
        print(f"  ms-economic: costo S/ {costo} por persona -> {puntos} puntos (assessment {str(aid)[:8]})")
    return {"event_id": u("completed", msg["evaluation_id"]), "event_type": "EconomicEvaluationCompleted",
            "evaluation_id": msg["evaluation_id"], "economic_assessment_id": str(aid),
            "cost_per_beneficiary_pen": str(costo), "score_0_100": str(puntos),
            "explanation": expl, "algorithm_version": ALGORITMO}


# ---------------- ms-platform: paso 7 ----------------
def recibir_resultado(plat, res: dict) -> None:
    with plat.transaction():
        nuevo = plat.execute("INSERT INTO inbox_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING event_id",
                             (res["event_id"],)).fetchone()
        if nuevo is None:
            print("  ms-platform: resultado repetido (inbox) -> no se vuelve a aplicar")
            return
        plat.execute("""INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id,
                        cost_per_beneficiary_pen, score_0_100, explanation, algorithm_version)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (evaluation_id) DO NOTHING""",
                     (res["evaluation_id"], res["economic_assessment_id"], res["cost_per_beneficiary_pen"],
                      res["score_0_100"], res["explanation"], res["algorithm_version"]))
        plat.execute("UPDATE evaluations SET status='completed', started_at=COALESCE(started_at, requested_at), finished_at=now() WHERE id=%s",
                     (res["evaluation_id"],))
        plat.execute("""UPDATE projects SET status='evaluated', updated_at=now() WHERE id =
                        (SELECT pv.project_id FROM evaluations e JOIN project_versions pv ON pv.id=e.project_version_id WHERE e.id=%s)""",
                     (res["evaluation_id"],))
        plat.execute("""INSERT INTO audit_events (actor_user_id, action, entity_type, entity_id, details)
                        VALUES (NULL,'EVALUATION_COMPLETED','evaluation',%s,%s)""",
                     (res["evaluation_id"], Jsonb({"score": res["score_0_100"]})))
        print(f"  ms-platform: evaluacion {res['evaluation_id'][:8]} completada")


if __name__ == "__main__":
    duplicar = "--duplicar" in sys.argv
    with conectar("platform") as plat, conectar("economic") as eco:
        plat.autocommit = eco.autocommit = True
        print("1) ms-platform solicita evaluaciones")
        solicitar(plat)
        print("2) ms-platform publica el outbox" + (" (REENVIO DUPLICADO)" if duplicar else ""))
        mensajes = publicar(plat, duplicar)
        print("3) ms-economic procesa y 4) ms-platform recibe")
        for m in mensajes:
            recibir_resultado(plat, evaluar_economico(eco, m))
    print("Listo.")
