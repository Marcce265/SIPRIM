-- =========================================================
-- PMV 1 · platform_db · datos semilla (ficticios)
-- Proyecto A: S/ 120 000 y 600 beneficiarios -> S/ 200 por persona
-- Proyecto B: S/  90 000 y 300 beneficiarios -> S/ 300 por persona
-- Politica activa v1: ECONOMIC = 100 %, excelente S/ 200, inaceptable S/ 500
-- created_by_user_id = UUID de las cuentas semilla de auth_db (sin FK)
-- =========================================================
INSERT INTO criteria_versions (id, version_number, status, excellent_cost_pen, unacceptable_cost_pen, created_by_user_id, activated_at)
VALUES ('c0000000-0000-4000-a000-000000000001', 1, 'active', 200.00, 500.00,
        '10000000-0000-4000-a000-000000000001', now())
ON CONFLICT (version_number) DO NOTHING;

INSERT INTO criterion_weights (criteria_version_id, criterion_code, weight_percent)
VALUES ('c0000000-0000-4000-a000-000000000001', 'ECONOMIC', 100.00)
ON CONFLICT DO NOTHING;

INSERT INTO projects (id, code, created_by_user_id, status) VALUES
    ('a0000000-0000-4000-a000-00000000000a', 'PRY-A', '10000000-0000-4000-a000-000000000002', 'ready'),
    ('a0000000-0000-4000-a000-00000000000b', 'PRY-B', '10000000-0000-4000-a000-000000000002', 'ready')
ON CONFLICT (code) DO NOTHING;

INSERT INTO project_versions (id, project_id, version_number, title, description, estimated_budget_pen, beneficiaries_count, created_by_user_id) VALUES
    ('b0000000-0000-4000-a000-00000000000a', 'a0000000-0000-4000-a000-00000000000a', 1,
     'Proyecto A - Mejoramiento de losa deportiva (prueba)', 'Dato ficticio para el PMV 1', 120000.00, 600,
     '10000000-0000-4000-a000-000000000002'),
    ('b0000000-0000-4000-a000-00000000000b', 'a0000000-0000-4000-a000-00000000000b', 1,
     'Proyecto B - Ampliacion de veredas (prueba)', 'Dato ficticio para el PMV 1', 90000.00, 300,
     '10000000-0000-4000-a000-000000000002')
ON CONFLICT (project_id, version_number) DO NOTHING;
