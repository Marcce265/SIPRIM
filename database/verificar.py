"""Pruebas de aceptacion del modelo (seccion 11) a nivel de base de datos.

Uso:  python database/verificar.py      (ejecutar despues de aplicar.py y simular_flujo.py)
"""

from decimal import Decimal

import psycopg
from _comun import conectar

resultados = []


def caso(n, nombre, ok, detalle=""):
    resultados.append(ok)
    print(
        f"[{'PASA' if ok else 'FALLA'}] Prueba {n}: {nombre}"
        + (f" -> {detalle}" if detalle else "")
    )


def rechaza(conn, sql, params=()):
    try:
        with conn.transaction():
            conn.execute(sql, params)
            raise RuntimeError("no rechazado")
    except psycopg.errors.CheckViolation:
        return True
    except RuntimeError:
        return False


with (
    conectar("auth") as auth,
    conectar("platform") as plat,
    conectar("economic") as eco,
):
    for c in (auth, plat, eco):
        c.autocommit = True

    roles = dict(
        auth.execute("""SELECT u.email, r.code FROM users u JOIN user_roles ur ON ur.user_id=u.id
                                 JOIN roles r ON r.id=ur.role_id""").fetchall()
    )
    caso(
        1,
        "cuentas ADMIN y PLANNER con hash Argon2id",
        roles.get("admin@siprim.test") == "ADMIN"
        and roles.get("planner@siprim.test") == "PLANNER"
        and auth.execute(
            "SELECT bool_and(password_hash LIKE '$argon2id$%') FROM users"
        ).fetchone()[0],
        ", ".join(f"{k} = {v}" for k, v in sorted(roles.items())),
    )

    pv = dict(
        (c, (b, n))
        for c, b, n in plat.execute("""SELECT p.code, pv.estimated_budget_pen, pv.beneficiaries_count
        FROM projects p JOIN project_versions pv ON pv.project_id=p.id AND pv.version_number=1""").fetchall()
    )
    caso(
        2,
        "proyectos A y B con version 1",
        pv.get("PRY-A") == (Decimal("120000.00"), 600)
        and pv.get("PRY-B") == (Decimal("90000.00"), 300),
        ", ".join(f"{k}: S/ {b} y {n} personas" for k, (b, n) in sorted(pv.items())),
    )

    pesos = plat.execute("""SELECT cv.version_number, SUM(w.weight_percent), bool_or(w.criterion_code='ECONOMIC' AND w.weight_percent=100)
        FROM criteria_versions cv JOIN criterion_weights w ON w.criteria_version_id=cv.id WHERE cv.status='active'
        GROUP BY cv.version_number""").fetchall()
    caso(
        3,
        "politica activa con pesos = 100 % y ECONOMIC = 100",
        len(pesos) == 1 and pesos[0][1] == 100 and pesos[0][2],
        f"v{pesos[0][0]} suma {pesos[0][1]} %" if pesos else "sin politica",
    )

    eval_ab = dict(
        plat.execute(
            """SELECT e.id::text, p.code
            FROM evaluations e
            JOIN project_versions pv ON pv.id = e.project_version_id
            JOIN projects p ON p.id = pv.project_id
            WHERE p.code IN ('PRY-A', 'PRY-B')"""
        ).fetchall()
    )
    filas = dict(
        (str(a), (c, s))
        for a, c, s in eco.execute(
            "SELECT evaluation_id, cost_per_beneficiary_pen, score_0_100 FROM economic_assessments"
        ).fetchall()
    )
    filas_ab = {eval_ab[e]: v for e, v in filas.items() if e in eval_ab}
    costos_ab = sorted(filas_ab.values())
    caso(
        4,
        "costo/persona 200 y 300; puntos 100 y 66,67",
        costos_ab
        == [
            (Decimal("200.00"), Decimal("100.00")),
            (Decimal("300.00"), Decimal("66.67")),
        ],
        ", ".join(f"{k}: S/ {c} -> {s} pts" for k, (c, s) in sorted(filas_ab.items())),
    )

    proy = {
        str(e): (str(a), c, s)
        for e, a, c, s in plat.execute(
            "SELECT evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100 FROM economic_result_projections"
        ).fetchall()
    }
    ids_eco = {
        str(e): str(i)
        for e, i in eco.execute(
            "SELECT evaluation_id, id FROM economic_assessments"
        ).fetchall()
    }
    caso(
        5,
        "proyecciones de platform_db = resultados reales de economic_db",
        bool(proy)
        and all(
            ids_eco.get(e) == v[0] and filas[e] == (v[1], v[2]) for e, v in proy.items()
        ),
        f"{len(proy)} proyecciones",
    )

    n_ev = plat.execute("SELECT count(*) FROM evaluations").fetchone()[0]
    n_as = eco.execute("SELECT count(*) FROM economic_assessments").fetchone()[0]
    caso(
        6,
        "sin duplicados: 1 evaluacion = 1 assessment = 1 proyeccion",
        n_ev == n_as == len(proy) >= 2,
        f"evaluaciones={n_ev}, assessments={n_as}, proyecciones={len(proy)}",
    )

    try:  # se prueba dentro de una transaccion que se deshace al final
        with plat.transaction():
            plat.execute("""INSERT INTO project_versions (id, project_id, version_number, title, estimated_budget_pen,
                beneficiaries_count, created_by_user_id) SELECT gen_random_uuid(), id, 2, 'Proyecto A v2', 150000, 600,
                created_by_user_id FROM projects WHERE code='PRY-A'""")
            v = plat.execute("""SELECT max(pv.version_number), (SELECT pv1.estimated_budget_pen FROM evaluations e
                JOIN project_versions pv1 ON pv1.id=e.project_version_id JOIN projects p1 ON p1.id=pv1.project_id
                WHERE p1.code='PRY-A' LIMIT 1) FROM project_versions pv JOIN projects p ON p.id=pv.project_id
                WHERE p.code='PRY-A'""").fetchone()
            raise psycopg.Rollback()
    except Exception:
        v = None
    caso(
        7,
        "corregir crea version 2 y la evaluacion anterior conserva v1",
        v is not None and v[0] == 2 and v[1] == Decimal("120000.00"),
        f"version maxima={v[0]}, evaluacion usa S/ {v[1]}" if v else "",
    )

    pid = plat.execute("SELECT id FROM projects WHERE code='PRY-A'").fetchone()[0]
    neg = rechaza(
        plat,
        """INSERT INTO project_versions (id, project_id, version_number, title, estimated_budget_pen,
                           beneficiaries_count, created_by_user_id) VALUES (gen_random_uuid(), %s, 99, 'x', -1, 10, gen_random_uuid())""",
        (pid,),
    )
    cero = rechaza(
        plat,
        """INSERT INTO project_versions (id, project_id, version_number, title, estimated_budget_pen,
                            beneficiaries_count, created_by_user_id) VALUES (gen_random_uuid(), %s, 98, 'x', 1000, 0, gen_random_uuid())""",
        (pid,),
    )
    inv = rechaza(
        plat,
        """INSERT INTO criteria_versions (id, version_number, excellent_cost_pen, unacceptable_cost_pen,
                           created_by_user_id) VALUES (gen_random_uuid(), 99, 500, 200, gen_random_uuid())""",
    )
    caso(
        8,
        "rechaza presupuesto negativo, beneficiarios 0 y umbrales invertidos",
        neg and cero and inv,
        f"negativo={neg}, cero={cero}, invertidos={inv}",
    )

    territoriales = plat.execute(
        """SELECT count(*) FROM project_versions
        WHERE location_description IS NOT NULL AND proposed_land_use IS NOT NULL
          AND territorial_data_origin='simulated'"""
    ).fetchone()[0]
    sin_evidencia = rechaza(
        plat,
        """INSERT INTO zoning_review_requests
        (id,project_version_id,requested_by_user_id,idempotency_key,status,compatible,limitations)
        SELECT gen_random_uuid(),pv.id,pv.created_by_user_id,'prueba-sin-evidencia',
               'reviewed',TRUE,'Prueba de restriccion'
        FROM project_versions pv JOIN projects p ON p.id=pv.project_id
        WHERE p.code='PRY-A' AND pv.version_number=1""",
    )
    caso(
        9,
        "HU1.11 conserva datos territoriales y prohibe una conclusion sin evidencia",
        territoriales >= 2 and sin_evidencia,
        f"versiones territoriales={territoriales}, conclusion sin evidencia rechazada={sin_evidencia}",
    )


    legal_role = auth.execute(
        """SELECT count(*) FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE u.email = 'legal@siprim.test' AND r.code = 'LEGAL_ADVISOR'"""
    ).fetchone()[0]

    normativos = plat.execute(
        """SELECT count(*),
                  count(*) FILTER (WHERE has_alert = TRUE),
                  count(DISTINCT short_code)
        FROM normative_documents
        WHERE in_force = TRUE AND data_origin = 'simulated'"""
    ).fetchone()

    origen_invalido = rechaza(
        plat,
        """INSERT INTO normative_documents
        (id, document_name, short_code, version, topic, content, data_origin)
        VALUES ('TEST-ERR', 'Norma Test', 'TEST', 'v1', 'Tema', 'Contenido', 'origen_falso')""",
    )

    p10_ok = bool(
        legal_role == 1
        and normativos[0] >= 24
        and normativos[1] >= 2
        and normativos[2] >= 4
        and origen_invalido
    )

    caso(
        10,
        "HU2.1 rol LEGAL_ADVISOR, 24 fragmentos normativos con alertas y origen restringido",
        p10_ok,
        f"legal={legal_role}, fragmentos={normativos[0]}, alertas={normativos[1]}, grupos={normativos[2]}, rechazo={origen_invalido}",
    )

    print(f"\nResultado: {sum(resultados)} de {len(resultados)} pruebas pasaron")
