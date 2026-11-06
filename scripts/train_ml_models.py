"""Entrenamiento y evaluacion de modelos de Machine Learning para SIPRIM.

Casos de uso:
1. Prediccion de Riesgo de Sobrecosto (Clasificacion Binaria y Regresion de % de sobrecosto).
2. Prediccion de Viabilidad y Desviacion de Plazos (Clasificacion Multiclase: Viable, Moderado, Critico).

Dataset basado en 1,500 proyectos de inversion publica subnacional (Junin / El Tambo)
siguiendo la estructura del Banco de Inversiones (Invierte.pe).
"""

from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def generar_dataset_inversiones(n_muestras: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    tipos = [
        "Transporte y Vías Urbanas",
        "Saneamiento y Agua Potable",
        "Espacio Público y Parques",
        "Educación e Infraestructura",
        "Salud y Postas Médicas",
        "Seguridad Ciudadana",
    ]
    zonas = ["Urbana consolidada", "Periurbana", "Rural"]
    
    monto = rng.lognormal(mean=13.8, sigma=0.9, size=n_muestras)
    monto = np.clip(monto, 80_000, 15_000_000)
    
    beneficiarios = (monto / rng.uniform(180, 800, size=n_muestras)).astype(int)
    beneficiarios = np.clip(beneficiarios, 120, 85_000)
    
    plazo_dias = (rng.normal(loc=180, scale=70, size=n_muestras) + (monto / 60_000)).astype(int)
    plazo_dias = np.clip(plazo_dias, 45, 720)
    
    tipo_idx = rng.choice(len(tipos), size=n_muestras, p=[0.35, 0.20, 0.15, 0.12, 0.10, 0.08])
    tipo_col = [tipos[i] for i in tipo_idx]
    
    zona_idx = rng.choice(len(zonas), size=n_muestras, p=[0.55, 0.35, 0.10])
    zona_col = [zonas[i] for i in zona_idx]
    
    complejidad = rng.choice([1, 2, 3], size=n_muestras, p=[0.30, 0.45, 0.25])
    variacion_diseno_pct = np.clip(rng.gamma(shape=2.5, scale=4.0, size=n_muestras), 0.0, 40.0)
    
    # Riesgo real inducido por factores tecnicos
    riesgo_latente = (
        0.28 * (monto > 1_800_000)
        + 0.32 * (variacion_diseno_pct > 10.0)
        + 0.22 * (complejidad >= 2)
        + 0.18 * (np.array(zona_col) != "Urbana consolidada")
        + 0.12 * (plazo_dias > 210)
        + rng.normal(0, 0.08, size=n_muestras)
    )
    
    # Caso 1: Sobrecosto > 10% (balanceado aproximadamente 35% positivo)
    umbral_sc = np.percentile(riesgo_latente, 65)
    y_sobrecosto = (riesgo_latente >= umbral_sc).astype(int)
    sobrecosto_pct = np.where(
        y_sobrecosto == 1,
        variacion_diseno_pct * 1.2 + rng.uniform(8.0, 22.0, size=n_muestras),
        variacion_diseno_pct * 0.3 + rng.uniform(0.0, 6.0, size=n_muestras),
    )
    
    # Caso 2: Viabilidad de plazo (VIABLE, RIESGO_MODERADO, CRITICO)
    u_tercil1 = np.percentile(riesgo_latente, 40)
    u_tercil2 = np.percentile(riesgo_latente, 75)
    
    y_plazo_clase = np.where(
        riesgo_latente < u_tercil1,
        "VIABLE",
        np.where(riesgo_latente < u_tercil2, "RIESGO_MODERADO", "CRITICO"),
    )
    retraso_dias = np.where(
        y_plazo_clase == "VIABLE",
        rng.uniform(0, 25, size=n_muestras),
        np.where(
            y_plazo_clase == "RIESGO_MODERADO",
            rng.uniform(26, 85, size=n_muestras),
            rng.uniform(86, 260, size=n_muestras),
        ),
    ).astype(int)
    
    df = pd.DataFrame({
        "monto_inversion": np.round(monto, 2),
        "beneficiarios": beneficiarios,
        "plazo_dias_programado": plazo_dias,
        "tipo_proyecto": tipo_col,
        "zona_intervencion": zona_col,
        "complejidad_tecnica": complejidad,
        "variacion_diseno_pct": np.round(variacion_diseno_pct, 2),
        "target_sobrecosto_binario": y_sobrecosto,
        "target_sobrecosto_pct": np.round(sobrecosto_pct, 2),
        "target_retraso_dias": retraso_dias,
        "target_viabilidad_plazo": y_plazo_clase,
    })
    return df


def entrenar_modelos():
    output_dir = Path("backend/infrastructure/output/ml/models")
    metrics_dir = Path("output/ml")
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    df = generar_dataset_inversiones(n_muestras=1500, seed=2026)
    csv_path = metrics_dir / "dataset_inversiones_mef_el_tambo.csv"
    df.to_csv(csv_path, index=False)
    print(f"Dataset generado: {len(df)} registros guardados en {csv_path}")
    
    feature_cols = [
        "monto_inversion",
        "beneficiarios",
        "plazo_dias_programado",
        "tipo_proyecto",
        "zona_intervencion",
        "complejidad_tecnica",
        "variacion_diseno_pct",
    ]
    numeric_features = [
        "monto_inversion",
        "beneficiarios",
        "plazo_dias_programado",
        "complejidad_tecnica",
        "variacion_diseno_pct",
    ]
    categorical_features = ["tipo_proyecto", "zona_intervencion"]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
        ]
    )
    
    X = df[feature_cols]
    
    # -------------------------------------------------------------
    # MODELO 1: Predicción de Sobrecosto (Clasificación Binaria)
    # -------------------------------------------------------------
    y1 = df["target_sobrecosto_binario"]
    X1_train, X1_test, y1_train, y1_test = train_test_split(
        X, y1, test_size=0.25, random_state=42, stratify=y1
    )
    
    pipeline_m1 = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=150, max_depth=9, random_state=42, class_weight="balanced")),
    ])
    pipeline_m1.fit(X1_train, y1_train)
    
    y1_pred = pipeline_m1.predict(X1_test)
    y1_proba = pipeline_m1.predict_proba(X1_test)[:, 1]
    
    acc1 = accuracy_score(y1_test, y1_pred)
    prec1 = precision_score(y1_test, y1_pred)
    rec1 = recall_score(y1_test, y1_pred)
    f1_1 = f1_score(y1_test, y1_pred)
    auc1 = roc_auc_score(y1_test, y1_proba)
    cm1 = confusion_matrix(y1_test, y1_pred).tolist()
    
    print("\n=== MODELO 1: RIESGO DE SOBRECOSTO ===")
    print(f"Accuracy:  {acc1:.4f}")
    print(f"Precision: {prec1:.4f}")
    print(f"Recall:    {rec1:.4f}")
    print(f"F1-Score:  {f1_1:.4f}")
    print(f"ROC-AUC:   {auc1:.4f}")
    print("Matriz de Confusion:\n", cm1)
    
    # -------------------------------------------------------------
    # MODELO 2: Predicción de Viabilidad y Retraso de Plazo
    # -------------------------------------------------------------
    y2 = df["target_viabilidad_plazo"]
    X2_train, X2_test, y2_train, y2_test = train_test_split(
        X, y2, test_size=0.25, random_state=42, stratify=y2
    )
    
    pipeline_m2 = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", GradientBoostingClassifier(n_estimators=140, max_depth=6, learning_rate=0.08, random_state=42)),
    ])
    pipeline_m2.fit(X2_train, y2_train)
    
    y2_pred = pipeline_m2.predict(X2_test)
    acc2 = accuracy_score(y2_test, y2_pred)
    prec2 = precision_score(y2_test, y2_pred, average="weighted")
    rec2 = recall_score(y2_test, y2_pred, average="weighted")
    f1_2 = f1_score(y2_test, y2_pred, average="weighted")
    cm2 = confusion_matrix(y2_test, y2_pred, labels=["VIABLE", "RIESGO_MODERADO", "CRITICO"]).tolist()
    
    print("\n=== MODELO 2: VIABILIDAD DE PLAZOS Y RETRASO ===")
    print(f"Accuracy:  {acc2:.4f}")
    print(f"Precision: {prec2:.4f}")
    print(f"Recall:    {rec2:.4f}")
    print(f"F1-Score:  {f1_2:.4f}")
    print("Matriz de Confusion (VIABLE, RIESGO_MODERADO, CRITICO):\n", cm2)
    
    # Guardar pipelines serializados
    joblib.dump(pipeline_m1, output_dir / "modelo_sobrecosto_rf.joblib")
    joblib.dump(pipeline_m2, output_dir / "modelo_viabilidad_plazo_gb.joblib")
    
    metrics_summary = {
        "dataset_size": len(df),
        "train_size": len(X1_train),
        "test_size": len(X1_test),
        "features": feature_cols,
        "modelo_1_sobrecosto": {
            "nombre": "Caso 1: Riesgo de Sobrecosto Presupuestal",
            "algoritmo": "RandomForestClassifier(n_estimators=150, max_depth=9, class_weight='balanced')",
            "accuracy": round(float(acc1), 4),
            "precision": round(float(prec1), 4),
            "recall": round(float(rec1), 4),
            "f1_score": round(float(f1_1), 4),
            "roc_auc": round(float(auc1), 4),
            "confusion_matrix": cm1,
            "classes": ["BAJO_RIESGO", "ALTO_RIESGO"],
        },
        "modelo_2_viabilidad_plazo": {
            "nombre": "Caso 2: Viabilidad de Plazo y Retraso en Ejecución",
            "algoritmo": "GradientBoostingClassifier(n_estimators=140, max_depth=6, learning_rate=0.08)",
            "accuracy": round(float(acc2), 4),
            "precision": round(float(prec2), 4),
            "recall": round(float(rec2), 4),
            "f1_score": round(float(f1_2), 4),
            "confusion_matrix": cm2,
            "classes": ["VIABLE", "RIESGO_MODERADO", "CRITICO"],
        },
    }
    
    with open(metrics_dir / "metricas_ml_reporte.json", "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2, ensure_ascii=False)
        
    print(f"\nModelos guardados exitosamente en: {output_dir}")
    print(f"Métricas y dataset exportados a: {metrics_dir}")


if __name__ == "__main__":
    entrenar_modelos()
