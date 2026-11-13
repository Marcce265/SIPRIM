"""Train and export portable models using the MEF's actual closed investments.

Usage: python scripts/train_predictive_mef.py /path/CIERRE_INVERSIONES.csv
Training dependencies are separate from the serverless inference runtime.
"""
from __future__ import annotations

import gzip
import base64
import hashlib
import json
from datetime import date
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, mean_absolute_error, roc_auc_score

SOURCE = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/CIERRE_INVERSIONES.csv"
ROOT = Path(__file__).resolve().parents[1]
CATS = ["FUNCION", "DEPARTAMENTO", "DES_MODALIDAD", "TIPO_INVERSION"]


def tree_dict(tree):
    t = tree.tree_
    return {"left": t.children_left.tolist(), "right": t.children_right.tolist(),
            "feature": t.feature.tolist(), "threshold": t.threshold.tolist(),
            "value": t.value.reshape(t.node_count, -1).tolist()}


def main(path: Path):
    raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    columns = ["CODIGO_UNICO", "NIVEL", "CULMINADA", "FECHA_VIABILIDAD", "MONTO_VIABLE",
               "TOTAL_LIQUIDACION", "INICIO_EJEC_FISICA", "CULMINA_EJEC_FISICA", *CATS]
    df = pd.read_csv(path, usecols=columns, dtype=str).fillna("")
    total = len(df)
    for col in ["MONTO_VIABLE", "TOTAL_LIQUIDACION"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["FECHA_VIABILIDAD", "INICIO_EJEC_FISICA", "CULMINA_EJEC_FISICA"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["duration_days"] = (df.CULMINA_EJEC_FISICA - df.INICIO_EJEC_FISICA).dt.days
    today = pd.Timestamp(date.today())
    df = df[(df.NIVEL == "GL") & df.CULMINADA.isin(["SÍ", "SI"])
            & df.MONTO_VIABLE.between(10000, 10_000_000_000)
            & df.TOTAL_LIQUIDACION.between(1, 20_000_000_000)
            & df.duration_days.between(1, 3650)
            & (df.FECHA_VIABILIDAD <= df.INICIO_EJEC_FISICA)
            & (df.CULMINA_EJEC_FISICA <= today)]
    for col in CATS:
        df = df[df[col].str.strip().ne("")]
    df = df.sort_values(["FECHA_VIABILIDAD", "CODIGO_UNICO"]).drop_duplicates("CODIGO_UNICO", keep="last")
    if len(df) < 300:
        raise ValueError("No hay suficientes registros verificables para entrenar")
    split = int(len(df) * .8)
    # Keep a complete calendar year on one side of the temporal split.
    cutoff = int(df.iloc[split].FECHA_VIABILIDAD.year)
    train = df[df.FECHA_VIABILIDAD.dt.year < cutoff]
    test = df[df.FECHA_VIABILIDAD.dt.year >= cutoff]
    if min(len(train), len(test)) < 100:
        raise ValueError("Partición temporal insuficiente")
    categories = {col: sorted(train[col].unique().tolist()) for col in CATS}

    def vector(frame):
        parts = [np.log1p(frame.MONTO_VIABLE.to_numpy(float)).reshape(-1, 1)]
        for col, options in categories.items():
            parts.append(np.column_stack([(frame[col] == option).astype(float) for option in options]))
        return np.column_stack(parts)

    x_train, x_test = vector(train), vector(test)
    y_train = (train.TOTAL_LIQUIDACION > train.MONTO_VIABLE * 1.1).astype(int)
    y_test = (test.TOTAL_LIQUIDACION > test.MONTO_VIABLE * 1.1).astype(int)
    if min(y_train.value_counts().min(), y_test.value_counts().min()) < 20:
        raise ValueError("Insuficientes resultados de una clase")
    rf = RandomForestClassifier(n_estimators=100, max_depth=6, min_samples_leaf=20, random_state=42, n_jobs=-1)
    rf.fit(x_train, y_train)
    gb = GradientBoostingRegressor(n_estimators=120, max_depth=3, min_samples_leaf=20, loss="huber", random_state=42)
    gb.fit(x_train, np.log1p(train.duration_days.to_numpy(float)))
    proba = rf.predict_proba(x_test)[:, list(rf.classes_).index(1)]
    durations = np.expm1(gb.predict(x_test)).clip(1, 3650)
    median_days = float(train.duration_days.median())
    metrics = {
        "cost": {"accuracy": float(accuracy_score(y_test, proba >= .5)),
                 "balanced_accuracy": float(balanced_accuracy_score(y_test, proba >= .5)),
                 "roc_auc": float(roc_auc_score(y_test, proba)),
                 "brier_score": float(brier_score_loss(y_test, proba)),
                 "test_positive_rate": float(y_test.mean()),
                 "baseline_accuracy": float(accuracy_score(y_test, np.full(len(test), int(y_train.mean() >= .5))))},
        "duration": {"mae_days": float(mean_absolute_error(test.duration_days, durations)),
                     "median_baseline_mae_days": float(mean_absolute_error(test.duration_days, np.full(len(test), median_days)))}
    }
    metadata = {"schema_version": 1, "model_version": "mef-closed-" + raw_hash[:12],
        "trained_at": date.today().isoformat(), "source_url": SOURCE,
        "training_versions": {"scikit_learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        "source_sha256": raw_hash, "source_rows": total, "eligible_rows": len(df),
        "train_rows": len(train), "test_rows": len(test), "test_from_year": cutoff,
        "data_origin": "MEF: inversiones cerradas, gobiernos locales, culminadas y con liquidación registrada",
        "synthetic_data": False, "categories": categories,
        "budget_range": [float(train.MONTO_VIABLE.min()), float(train.MONTO_VIABLE.max())],
        "metrics": metrics,
        "cost_target": "TOTAL_LIQUIDACION > 1.10 × MONTO_VIABLE (liquidación frente a monto viable)",
        "duration_target": "Días entre INICIO_EJEC_FISICA y CULMINA_EJEC_FISICA",
        "limitations": [
            "Estudio observacional de inversiones locales cerradas; no certifica viabilidad municipal.",
            "La liquidación y el monto viable pueden diferir por cambios de alcance y precios; no prueba un sobrecosto de contrato.",
            "No se dispone aquí del plazo inicial programado: no se entrena un clasificador de retrasos reales.",
            "La duración se compara con el plazo ingresado; esa diferencia no es una probabilidad de retraso.",
            "La validación temporal no sustituye una evaluación prospectiva en El Tambo."]}
    package = {"metadata": metadata, "forest": [tree_dict(t) for t in rf.estimators_],
               "duration": {"initial": float(gb.init_.constant_[0, 0]),
                            "learning_rate": float(gb.learning_rate),
                            "trees": [tree_dict(t[0]) for t in gb.estimators_]}}
    dest = ROOT / "backend/infrastructure/output/ml_mef"
    dest.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(package, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    (dest / "model.b64").write_text(base64.encodebytes(gzip.compress(serialized, mtime=0)).decode())
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    # Public CUI and features/targets only: exclude names and contact/person fields.
    df[["CODIGO_UNICO", "FECHA_VIABILIDAD", "MONTO_VIABLE", "TOTAL_LIQUIDACION", "duration_days", *CATS]].to_csv(dest / "training_records.csv.gz", index=False, compression="gzip")
    parity_rows = []
    for _, row in test.iloc[:12].iterrows():
        xx = vector(pd.DataFrame([row]))
        parity_rows.append({"budget_pen": row.MONTO_VIABLE,
                           "categories": {col: row[col] for col in CATS},
                           "cost_probability": float(rf.predict_proba(xx)[0, 1]),
                           "duration_days": float(np.expm1(gb.predict(xx)[0]).clip(1, 3650))})
    (dest / "parity.json").write_text(json.dumps(parity_rows, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
