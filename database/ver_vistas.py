"""Muestra en la terminal las vistas en espanol de las tres bases.
Uso: python database/ver_vistas.py"""
from _comun import conectar

VISTAS = {"auth": ["vista_usuarios"],
          "platform": ["vista_proyectos", "vista_criterios", "vista_evaluaciones", "vista_auditoria"],
          "economic": ["vista_resultados_economicos", "vista_indicadores"]}

for base, vistas in VISTAS.items():
    with conectar(base) as conn:
        for vista in vistas:
            cur = conn.execute(f"SELECT * FROM {vista}")
            cols = [c.name for c in cur.description if c.name not in ("explicacion", "detalle", "formula")]
            idx = [i for i, c in enumerate(cur.description) if c.name in cols]
            filas = [[str(f[i])[:45] if f[i] is not None else "-" for i in idx] for f in cur.fetchall()]
            anchos = [max(len(c), *(len(f[j]) for f in filas)) if filas else len(c) for j, c in enumerate(cols)]
            print(f"\n=== {base}_db - {vista} ===")
            print("  ".join(c.ljust(a) for c, a in zip(cols, anchos)))
            print("  ".join("-" * a for a in anchos))
            for f in filas:
                print("  ".join(v.ljust(a) for v, a in zip(f, anchos)))
