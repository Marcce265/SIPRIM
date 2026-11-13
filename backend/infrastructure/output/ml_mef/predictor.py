"""Portable inference for the versioned MEF models (no pickle or heuristics)."""
from __future__ import annotations

from functools import lru_cache
import base64
import gzip
import json
import math
from pathlib import Path

from backend.domain.exceptions.pmv1_exceptions import ServicioNoDisponibleError

DIRECTORY = Path(__file__).parent


@lru_cache(maxsize=1)
def load_model() -> dict:
    try:
        packed = base64.b64decode((DIRECTORY / "model.b64").read_text(), validate=False)
        bundle = json.loads(gzip.decompress(packed))
        meta = bundle["metadata"]
        if meta["schema_version"] != 1 or meta["synthetic_data"] is not False:
            raise ValueError("Modelo no admitido")
        if not bundle["forest"] or not bundle["duration"]["trees"]:
            raise ValueError("Modelo incompleto")
        return bundle
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ServicioNoDisponibleError("Modelo ML no disponible. No se genera una predicción de respaldo.") from exc


def leaf(tree: dict, vector: list[float]) -> list[float]:
    node = 0
    while tree["left"][node] != -1:
        node = tree["left"][node] if vector[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
    return tree["value"][node]


def predict(budget_pen: float, categories: dict[str, str], planned_days: int | None = None) -> dict:
    bundle = load_model()
    metadata = bundle["metadata"]
    lo, hi = metadata["budget_range"]
    if not math.isfinite(budget_pen) or not lo <= budget_pen <= hi:
        raise ValueError(f"El presupuesto debe estar dentro del rango entrenado: S/ {lo:.2f} a S/ {hi:.2f}.")
    vector = [math.log1p(budget_pen)]
    for field, options in metadata["categories"].items():
        if categories.get(field) not in options:
            raise ValueError(f"Seleccione un valor admitido para {field}; no se reemplaza por un valor ficticio.")
        vector.extend(float(categories[field] == option) for option in options)
    # sklearn decision trees convert feature inputs to float32 before traversing.
    import struct
    vector = [struct.unpack("f", struct.pack("f", value))[0] for value in vector]
    probabilities = []
    for tree in bundle["forest"]:
        value = leaf(tree, vector)
        probabilities.append(value[1] / sum(value))
    risk = sum(probabilities) / len(probabilities)
    duration_model = bundle["duration"]
    log_duration = duration_model["initial"] + duration_model["learning_rate"] * sum(leaf(t, vector)[0] for t in duration_model["trees"])
    days = min(3650., max(1., math.expm1(log_duration)))
    return {"model_version": metadata["model_version"],
            "source_sha256": metadata["source_sha256"],
            "budget_pen": budget_pen, "categories": categories,
            "cost_probability": risk,
            "cost_class": "SUPERA_10_PCT" if risk >= .5 else "NO_SUPERA_10_PCT",
            "estimated_duration_days": days,
            "planned_days": planned_days,
            "difference_days": days - planned_days if planned_days is not None else None,
            "metrics": metadata["metrics"], "limitations": metadata["limitations"]}
