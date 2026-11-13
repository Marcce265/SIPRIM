# Módulo predictivo integrado en SIPRIM

## Uso

Un planificador o administrador autenticado abre **Predicciones ML**, consulta un expediente real por su código o UUID y confirma función, departamento, modalidad y tipo de inversión según su documentación. El presupuesto se lee de la versión registrada en PostgreSQL y no se acepta un presupuesto arbitrario en la petición. Se puede indicar el plazo programado para compararlo con la duración estimada.

La predicción se ejecuta en el backend y se conserva en `audit_events`, acción `ML_PREDICTION_CREATED`, con usuario, instante, entradas, resultado, versión del expediente y versión del modelo. Al consultar de nuevo se recupera la última predicción de esa misma versión. No requiere tablas nuevas, semillas ni cambios en datos existentes. Si el proyecto no existe, cambió de versión, el usuario no tiene permiso o el modelo no carga, se devuelve un error; no hay respuesta de demostración ni sustitución por Gemini.

## Modelos y significado de las salidas

1. **Random Forest**, 100 árboles, profundidad máxima 6: estima la probabilidad de que `TOTAL_LIQUIDACION > 1.10 × MONTO_VIABLE` en una inversión cerrada. La liquidación puede diferir del monto viable por modificaciones de alcance y precios. No equivale a demostrar sobrecosto contractual, ni el porcentaje es un aumento presupuestario estimado. La exactitud no mejora la referencia mayoritaria: se identifica como señal exploratoria.
2. **Gradient Boosting**, 120 árboles de profundidad 3 sobre `log(1 + duración)`: estima días entre `INICIO_EJEC_FISICA` y `CULMINA_EJEC_FISICA`. La diferencia con el plazo indicado por el usuario es una comparación, no un clasificador entrenado de retrasos. La fuente no aporta el plazo original para entrenar ese objetivo de manera verificable.

No se usan los modelos sintéticos ni los fallbacks de `feature/u3-ml-sp`. La API no usa pickle ni requiere scikit-learn en producción: recorre los árboles exportados a JSON. Una prueba compara las salidas con scikit-learn sobre 12 registros reservados, con tolerancias de 1e-12 para probabilidad y 1e-8 para duración.

## Datos reales y reproducibilidad

Fuente oficial del MEF:
https://fs.datosabiertos.mef.gob.pe/datastorefiles/CIERRE_INVERSIONES.csv

Catálogo:
https://www.datosabiertos.gob.pe/dataset/inversiones-en-estado-cerrado-registradas-en-el-banco-de-inversiones

Descargado el 13/11/2026. Archivo original: 120.472.558 bytes, 121.048 filas. SHA-256: `a01d020078384f10db31eea50f228c46a5acb3ab1bf295d7755211460e1febc3`. Son datos públicos de inversiones cerradas; no registros generados aleatoriamente. Conservar atribución al Ministerio de Economía y Finanzas.

Filtros: gobierno local, culminada, monto viable entre S/10.000 y S/10.000 millones, liquidación positiva de hasta S/20.000 millones, duración física entre 1 y 3.650 días, viabilidad anterior o igual al inicio físico, culminación no posterior a la fecha de entrenamiento, y las cuatro categorías presentes. Un único registro por CUI. Los valores atípicos excluidos y las inversiones sin datos no se imputan como resultados favorables.

Se obtuvieron **19.654 inversiones**. División temporal por año de viabilidad: entrenamiento anterior a 2021 (**13.967**) y evaluación desde 2021 (**5.687**). CUI, fechas de resultado, liquidación y duración observada no son entradas del modelo. El script genera `training_records.csv.gz` con solo CUI, variables y objetivos utilizados; excluye responsables, contactos y nombres de personas. Ese archivo se regenera desde la fuente y no se requiere en producción. `metadata.json` registra procedencia y métricas; `parity.json` contiene 12 casos de evaluación para verificar la exportación. `model.b64` empaqueta los árboles JSON comprimidos como texto, sin ejecutar código serializado. No se insertan expedientes de ejemplo en la base de producción.

Validación temporal observada:

| Indicador | Modelo | Referencia |
|---|---:|---:|
| Exactitud de liquidación | 70,20 % | 70,20 % (clase mayoritaria) |
| AUC ROC de liquidación | 0,587 | 0,500 |
| Error absoluto medio de duración | 91,49 días | 111,10 días (mediana de entrenamiento) |

No se afirma validación prospectiva, calibración probabilística ni rendimiento específico garantizado en El Tambo. El conjunto es observacional y está condicionado a inversiones que llegaron a cierre y registraron liquidación. No representa todas las inversiones nuevas.

Para reproducir:

```bash
python -m pip install -r scripts/requirements-ml-training.txt
python scripts/train_predictive_mef.py /ruta/CIERRE_INVERSIONES.csv
python -m pytest backend/tests/test_predictive_ml.py
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

La descarga debe hacerse desde la fuente oficial y su hash debe cotejarse con esta versión antes de comparar resultados. Un nuevo corte de datos genera otra versión de modelo; no atribuirle las métricas de este corte.

## API

- `GET /api/v1/ml/model`: metadatos y categorías; lector autorizado.
- `POST /api/v1/ml/projects/{uuid}/predict`: predicción persistida; planificador/administrador.
- `GET /api/v1/ml/projects/{uuid}/latest`: último resultado para la versión vigente; lector autorizado.

El endpoint POST acepta `project_version_id`, `function`, `department`, `execution_mode`, `investment_type` y `planned_days` opcional. Rechaza campos adicionales, categorías desconocidas, presupuestos fuera del dominio de entrenamiento, fracciones de días y valores no positivos. No modifica el estado del expediente ni omite la revisión humana.
