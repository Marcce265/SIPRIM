#!/usr/bin/env python3
"""
Generador de diagramas de ingeniería para el informe SIPRIM U3 S12.
Genera diagramas de alta resolución:
1. Árbol de Problemas
2. Flujo de Navegación de Pantallas
3. Wireframes / Prototipos PMV1
4. Wireframes / Prototipos PMV2
5. Modelo Entidad-Relación (MER / ERD)
6. Diseño de Paquetes UML (Arquitectura Hexagonal)
7. Diseño de Despliegue con Nodos UML
8. Estructura de Desglose del Trabajo (EDT / WBS)
9. Cronograma Gantt Línea Base vs. Ejecución Real
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, BoxStyle

OUTPUT_DIR = "/home/marcee/.gemini/antigravity/scratch/SIPRIM/docs/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuración global de estilos
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8

def draw_rounded_box(ax, x, y, width, height, text, bg_color='#f8fafc', border_color='#334155', text_color='#0f172a', fontsize=9, fontweight='normal', ha='center', va='center', boxstyle="round,pad=0.3,rounding_size=0.15"):
    box = FancyBboxPatch((x, y), width, height, boxstyle=boxstyle,
                         facecolor=bg_color, edgecolor=border_color, linewidth=1.5, zorder=2)
    ax.add_patch(box)
    ax.text(x + width/2 if ha=='center' else x + 0.1, 
            y + height/2 if va=='center' else y + height - 0.2, 
            text, ha=ha, va=va, fontsize=fontsize, color=text_color, fontweight=fontweight, multialignment='center', zorder=3)

def draw_arrow(ax, x1, y1, x2, y2, color='#475569', width=1.5, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=width, shrinkA=3, shrinkB=3), zorder=1)

# -------------------------------------------------------------
# 1. ÁRBOL DE PROBLEMAS
# -------------------------------------------------------------
def generar_arbol_problemas():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=180)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Título
    ax.text(7, 9.6, "ÁRBOL DE PROBLEMAS — PRIORIZACIÓN DE PROYECTOS DE INVERSIÓN MUNICIPAL (SIPRIM)",
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')
    ax.text(7, 9.25, "Municipalidad Distrital de El Tambo · Huancayo · Junín",
            ha='center', va='center', fontsize=10, style='italic', color='#475569')

    # EFECTOS (Nivel Superior)
    ax.text(7, 8.8, "EFECTOS INDIRECTOS Y DIRECTOS (IMPACTO NEGATIVO)", ha='center', va='center',
            fontsize=10, fontweight='bold', color='#991b1b')

    efectos_sup = [
        "Pérdida de confianza ciudadana\ny conflictividad social en El Tambo",
        "Perjuicio económico y costo de\noportunidad en fondos públicos",
        "Brechas de infraestructura básica\n(salud, vías, educación) persistentes"
    ]
    for i, ef in enumerate(efectos_sup):
        draw_rounded_box(ax, 0.8 + i*4.3, 7.8, 3.8, 0.8, ef, bg_color='#fee2e2', border_color='#dc2626', text_color='#7f1d1d', fontsize=8.5, fontweight='bold')

    efectos_dir = [
        "Retrasos severos de 6 a 18 meses\nen entrega de obras públicas",
        "Sobrecostos presupuestales no previstos\n(adicionales de obra >20%)",
        "Paralización de proyectos por\nvicios legales o ambientales no advertidos"
    ]
    for i, ef in enumerate(efectos_dir):
        draw_rounded_box(ax, 0.8 + i*4.3, 6.5, 3.8, 0.8, ef, bg_color='#ffedd5', border_color='#ea580c', text_color='#9a3412', fontsize=8.5)
        # Flechas de efectos directos a indirectos
        draw_arrow(ax, 2.7 + i*4.3, 7.3, 2.7 + i*4.3, 7.8, color='#dc2626')

    # Flechas de problema central a efectos directos
    for i in range(3):
        draw_arrow(ax, 7, 5.2, 2.7 + i*4.3, 6.5, color='#ea580c', width=2)

    # PROBLEMA CENTRAL
    draw_rounded_box(ax, 1.5, 4.2, 11.0, 1.0,
                     "PROBLEMA CENTRAL:\nDeficiente, subjetivo y tardío proceso de evaluación y priorización de expedientes\nde proyectos de inversión pública en la Municipalidad Distrital de El Tambo",
                     bg_color='#1e293b', border_color='#0f172a', text_color='#ffffff', fontsize=10.5, fontweight='bold')

    # CAUSAS DIRECTAS (Nivel Inferior)
    ax.text(7, 3.8, "CAUSAS DIRECTAS Y RAÍCES DEL PROBLEMA", ha='center', va='center',
            fontsize=10, fontweight='bold', color='#1e40af')

    causas_dir = [
        "C1: Evaluación manual de expedientes\nlenta (4 a 6 horas c/u) y con\nalto sesgo discrecional",
        "C2: Carencia de modelos predictivos\n(Machine Learning) para anticipar\nsobrecostos y retrasos",
        "C3: Criterios evaluativos dispersos\nen silos aislados (económico,\nsocial, ambiental, legal)",
        "C4: Inexistencia de trazabilidad y\nauditoría formal con puntos de control\nhumano activo (HITL)"
    ]
    for i, c in enumerate(causas_dir):
        draw_rounded_box(ax, 0.5 + i*3.3, 2.4, 3.1, 1.0, c, bg_color='#dbeafe', border_color='#2563eb', text_color='#1e3a8a', fontsize=8)
        # Flechas de causa directa a problema central
        draw_arrow(ax, 2.05 + i*3.3, 3.4, 7, 4.2, color='#2563eb', width=1.5)

    # CAUSAS RAÍZ
    causas_raiz = [
        "Uso de hojas de cálculo\ny expedientes físicos en papel\nsin validación automatizada",
        "Falta de aprovechamiento del\nBanco de Inversiones MEF para\nentrenamiento analítico previo",
        "Reglamentos técnicos complejos\n(Ley 32069, Invierte.pe) no\nintegrados a la preevaluación",
        "Decisiones gerenciales sin registro\ncriptográfico ni bitácora de\nintervención en tiempo real"
    ]
    for i, cr in enumerate(causas_raiz):
        draw_rounded_box(ax, 0.5 + i*3.3, 0.8, 3.1, 1.1, cr, bg_color='#f1f5f9', border_color='#64748b', text_color='#334155', fontsize=7.8)
        draw_arrow(ax, 2.05 + i*3.3, 1.9, 2.05 + i*3.3, 2.4, color='#64748b')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_arbol_problemas.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 2. FLUJO DE NAVEGACIÓN DE PANTALLAS
# -------------------------------------------------------------
def generar_flujo_navegacion():
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=180)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.5)
    ax.axis('off')

    ax.text(7.5, 8.1, "FLUJO DE NAVEGACIÓN DE PANTALLAS DEL SISTEMA SIPRIM",
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')
    ax.text(7.5, 7.7, "Interacción UI / UX y Transiciones entre Pantallas y Roles de Usuario",
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # Fila 1: Login -> Dashboard -> Expedientes
    draw_rounded_box(ax, 0.8, 5.8, 2.8, 1.2, "1. Login Institucional\n(/login)\n• Autenticación JWT\n• Selección de Rol RBAC", bg_color='#e0e7ff', border_color='#4338ca', text_color='#312e81', fontweight='bold', fontsize=8.5)
    
    draw_rounded_box(ax, 4.4, 5.8, 2.9, 1.2, "2. Dashboard Cartera\n(/dashboard / /)\n• Resumen ejecutivo\n• KPIs de cartera\n• Visualización en Mapa", bg_color='#f0fdf4', border_color='#15803d', text_color='#14532d', fontweight='bold', fontsize=8.5)
    
    draw_rounded_box(ax, 8.1, 5.8, 2.9, 1.2, "3. Registro Expediente\n(/expedientes/nuevo)\n• Formulario metadatos\n• Validación de montos\n• Carga de doc. técnico", bg_color='#fef3c7', border_color='#d97706', text_color='#78350f', fontweight='bold', fontsize=8.5)

    draw_rounded_box(ax, 11.8, 5.8, 2.8, 1.2, "4. Preevaluación Multidim.\n(/expedientes/:id/eval)\n• Agente Económico\n• Agente Social y Amb.\n• Agente Legal / Normas", bg_color='#ffedd5', border_color='#c2410c', text_color='#7c2d12', fontweight='bold', fontsize=8.5)

    # Flechas Fila 1
    draw_arrow(ax, 3.6, 6.4, 4.4, 6.4, color='#334155', width=1.5)
    draw_arrow(ax, 7.3, 6.4, 8.1, 6.4, color='#334155', width=1.5)
    draw_arrow(ax, 11.0, 6.4, 11.8, 6.4, color='#334155', width=1.5)

    # Fila 2: Predicción ML -> Carga Masiva -> HITL -> Reporte
    draw_rounded_box(ax, 11.8, 3.6, 2.8, 1.3, "5. Predicción ML\n(/prediccion-ml)\n• Caso 1: Riesgo Sobrecosto\n• Caso 2: Viabilidad Plazos\n• Métricas de Inferencia", bg_color='#fae8ff', border_color='#a21caf', text_color='#701a75', fontweight='bold', fontsize=8.5)

    draw_rounded_box(ax, 8.1, 3.6, 2.9, 1.3, "6. Carga Masiva Transaccional\n(/procedimientos-masivos)\n• 500-1000 transacciones\n• Stored Procedure PostgreSQL\n• Log ACID de Auditoría", bg_color='#e0f2fe', border_color='#0284c7', text_color='#0369a1', fontweight='bold', fontsize=8.5)

    draw_rounded_box(ax, 4.4, 3.6, 2.9, 1.3, "7. Intervención HITL\n(/revision-humana)\n• Alertas legales críticas\n• Pausa de control\n• Aprobación Gerencial", bg_color='#fee2e2', border_color='#b91c1c', text_color='#7f1d1d', fontweight='bold', fontsize=8.5)

    draw_rounded_box(ax, 0.8, 3.6, 2.8, 1.3, "8. Dictamen y Ranking\n(/cartera/priorizada)\n• Ranking multidimensional\n• Exportación PDF/Excel\n• Bitácora con hash SHA", bg_color='#ecfdf5', border_color='#059669', text_color='#065f46', fontweight='bold', fontsize=8.5)

    # Flechas Fila 1 a Fila 2 y retrocesos
    draw_arrow(ax, 13.2, 5.8, 13.2, 4.9, color='#334155', width=1.5)
    draw_arrow(ax, 11.8, 4.25, 11.0, 4.25, color='#334155', width=1.5)
    draw_arrow(ax, 8.1, 4.25, 7.3, 4.25, color='#334155', width=1.5)
    draw_arrow(ax, 4.4, 4.25, 3.6, 4.25, color='#334155', width=1.5)

    # Retorno a Dashboard
    draw_arrow(ax, 2.2, 4.9, 5.5, 5.8, color='#059669', width=1.5, style='<->')

    # Panel de Configuración y Auditoría (Fila 3)
    draw_rounded_box(ax, 2.0, 1.2, 5.0, 1.4, "Panel de Configuración de Criterios y Pesos\n(/configuracion/criterios)\n• Gestión de ponderaciones (suma 100%)\n• Umbrales de viabilidad y tolerancia\n• Acceso exclusivo: Administrador del Sistema", bg_color='#f8fafc', border_color='#64748b', text_color='#1e293b', fontsize=8)

    draw_rounded_box(ax, 8.0, 1.2, 5.0, 1.4, "Catálogo Normativo y Auditoría Histórica\n(/normativa / /auditoria)\n• Consulta asistida de Ley 32069 e Invierte.pe\n• Trazabilidad inalterable de cada evaluación\n• Acceso: Auditor y Asesor Jurídico", bg_color='#f8fafc', border_color='#64748b', text_color='#1e293b', fontsize=8)

    draw_arrow(ax, 4.5, 2.6, 5.8, 3.6, color='#64748b', width=1.2)
    draw_arrow(ax, 10.5, 2.6, 9.5, 3.6, color='#64748b', width=1.2)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_flujo_navegacion.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 3. WIREFRAMES PROTOTIPOS PMV1
# -------------------------------------------------------------
def generar_wireframes_pmv1():
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), dpi=180)
    fig.suptitle("WIREFRAMES / PROTOTIPOS DE INTERFAZ — PRODUCTO MÍNIMO VIABLE 1 (PMV1)", fontsize=12, fontweight='bold', color='#0f172a', y=0.98)

    # UI 1: Login y Selección de Rol
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "SIPRIM — Acceso Institucional\nMunicipalidad Distrital de El Tambo", bg_color='#1e293b', border_color='#0f172a', text_color='#ffffff', fontsize=8.5, fontweight='bold')
    
    ax.text(1.2, 8.8, "Usuario / DNI:", fontsize=8, fontweight='bold')
    draw_rounded_box(ax, 1.2, 7.8, 7.6, 0.8, "planner@eltambo.gob.pe", bg_color='#f1f5f9', border_color='#cbd5e1', text_color='#334155', ha='left', fontsize=8)
    
    ax.text(1.2, 7.0, "Contraseña:", fontsize=8, fontweight='bold')
    draw_rounded_box(ax, 1.2, 6.0, 7.6, 0.8, "••••••••••••••••", bg_color='#f1f5f9', border_color='#cbd5e1', text_color='#334155', ha='left', fontsize=8)

    ax.text(1.2, 5.2, "Rol Seleccionado:", fontsize=8, fontweight='bold')
    draw_rounded_box(ax, 1.2, 4.2, 7.6, 0.8, "Planificador Municipal (OPMI)", bg_color='#e0e7ff', border_color='#6366f1', text_color='#3730a3', ha='left', fontsize=8)

    draw_rounded_box(ax, 2.0, 2.2, 6.0, 1.2, "[ Ingresar al Sistema ]", bg_color='#2563eb', border_color='#1d4ed8', text_color='#ffffff', fontweight='bold', fontsize=9)
    ax.text(5, 1.0, "HU-01: Autenticación por Roles RBAC", ha='center', fontsize=8, style='italic', color='#64748b')

    # UI 2: Registro de Expediente
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "Registro de Expediente Técnico\nNuevo Proyecto de Inversión (PMV1)", bg_color='#047857', border_color='#065f46', text_color='#ffffff', fontsize=8.5, fontweight='bold')

    campos = [
        ("Código Único Inversión (CUI):", "2548912"),
        ("Nombre del Proyecto:", "Mejoramiento Vial Av. Huancavelica"),
        ("Monto de Inversión (S/.):", "S/. 2,850,000.00"),
        ("Población Beneficiaria:", "14,500 habitantes"),
        ("Plazo Ejecución Estimado:", "180 días calendario")
    ]
    for i, (lab, val) in enumerate(campos):
        ax.text(1.0, 8.8 - i*1.3, lab, fontsize=7.5, fontweight='bold')
        draw_rounded_box(ax, 1.0, 8.1 - i*1.3, 8.0, 0.65, val, bg_color='#f8fafc', border_color='#cbd5e1', text_color='#334155', ha='left', fontsize=7.5)

    draw_rounded_box(ax, 1.5, 1.4, 7.0, 0.9, "[ Guardar y Validar Datos ]", bg_color='#059669', border_color='#047857', text_color='#ffffff', fontweight='bold', fontsize=8.5)
    ax.text(5, 0.8, "HU-02: Registro y Validación Sintáctica", ha='center', fontsize=8, style='italic', color='#64748b')

    # UI 3: Preevaluación Económica
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "Dictamen Económico PMV1\nEvaluación Determinista de Costo-Beneficio", bg_color='#b45309', border_color='#92400e', text_color='#ffffff', fontsize=8.5, fontweight='bold')

    draw_rounded_box(ax, 1.0, 7.4, 8.0, 1.8, "Puntuación Económica: 88.4 / 100\nEstado: RECOMENDADO PARA CARTERA\nVAN Social Estimado: S/. 1,420,000\nTIR Social: 14.8% (> tasa corte 8%)", bg_color='#fef3c7', border_color='#d97706', text_color='#78350f', fontsize=7.8, fontweight='bold')

    draw_rounded_box(ax, 1.0, 4.0, 8.0, 3.0, "Desglose por Criterios de Evaluación:\n• Eficiencia de Costo por Beneficiario: 92 pts\n• Sostenibilidad Operativa y Mtto.: 85 pts\n• Consistencia de Presupuesto Base: 88 pts\n\nFórmula Determinista: S(C) = ∑ w_i · c_i\nPonderaciones versionadas en platform_db", bg_color='#f1f5f9', border_color='#cbd5e1', text_color='#334155', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 1.5, 1.4, 7.0, 0.9, "[ Emitir Preevaluación Base ]", bg_color='#d97706', border_color='#b45309', text_color='#ffffff', fontweight='bold', fontsize=8.5)
    ax.text(5, 0.8, "HU-03: Preevaluación y Scoring Económico", ha='center', fontsize=8, style='italic', color='#64748b')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_wireframes_pmv1.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 4. WIREFRAMES PROTOTIPOS PMV2
# -------------------------------------------------------------
def generar_wireframes_pmv2():
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), dpi=180)
    fig.suptitle("WIREFRAMES / PROTOTIPOS DE INTERFAZ — PRODUCTO MÍNIMO VIABLE 2 (PMV2)", fontsize=12, fontweight='bold', color='#0f172a', y=0.98)

    # UI 1: Predicción Machine Learning
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "Módulo de Machine Learning\nPredicción de Riesgo y Viabilidad", bg_color='#701a75', border_color='#4a044e', text_color='#ffffff', fontsize=8.5, fontweight='bold')

    draw_rounded_box(ax, 0.9, 6.6, 8.2, 2.7, "CASO 1: Riesgo de Sobrecosto (Random Forest)\n• Probabilidad de Sobrecosto: 78.4%\n• Clasificación: RIESGO ALTO\n• Importancia de Atributos: Monto (42%),\n  Sector (28%), Duración (18%), Fase (12%)\n• Métrica Modelo: ROC-AUC 0.9690, Acc 91.7%", bg_color='#fdf4ff', border_color='#d946ef', text_color='#701a75', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 0.9, 3.4, 8.2, 2.7, "CASO 2: Viabilidad de Plazo (Gradient Boosting)\n• Categoría: RETRASO MODERADO (30-60 d)\n• Confianza: 84.2%\n• Factores de Riesgo: Estacionalidad de lluvia,\n  complejidad de saneamiento predial\n• Métrica Modelo: F1-score 0.7999, Acc 80.0%", bg_color='#eef2ff', border_color='#6366f1', text_color='#312e81', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 1.5, 1.4, 7.0, 0.9, "[ Ejecutar Inferencia ML ]", bg_color='#a21caf', border_color='#86198f', text_color='#ffffff', fontweight='bold', fontsize=8.5)
    ax.text(5, 0.8, "HU-04: Predicción ML (2 Casos de Uso)", ha='center', fontsize=8, style='italic', color='#64748b')

    # UI 2: Carga Masiva y Stored Procedures
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "Carga Masiva Transaccional\nProcedimientos Almacenados PostgreSQL", bg_color='#0369a1', border_color='#075985', text_color='#ffffff', fontsize=8.5, fontweight='bold')

    draw_rounded_box(ax, 1.0, 7.6, 8.0, 1.7, "Parámetros de Ejecución Masiva:\n• Cantidad objetivo: 750 transacciones\n• Procedimiento: sp_registrar_evaluacion_masiva\n• Modo Transaccional: ACID / Commit en lote", bg_color='#f0f9ff', border_color='#0ea5e9', text_color='#0369a1', ha='left', fontsize=7.5)

    draw_rounded_box(ax, 1.0, 3.8, 8.0, 3.4, "Telemetría de Rendimiento PostgreSQL:\n✓ Total Registros Procesados: 750\n✓ Tiempo Total: 12.36 milisegundos\n✓ Rendimiento: 23,331 TPS\n✓ Errores / Rollbacks: 0 (100% éxito)\n✓ Inserción en: ml_prediction_logs\n✓ Trazabilidad SHA-256 verificada", bg_color='#f8fafc', border_color='#cbd5e1', text_color='#0f172a', ha='left', fontsize=7.5, fontweight='bold')

    draw_rounded_box(ax, 1.5, 1.4, 7.0, 0.9, "[ Disparar Carga Masiva SP ]", bg_color='#0284c7', border_color='#0369a1', text_color='#ffffff', fontweight='bold', fontsize=8.5)
    ax.text(5, 0.8, "HU-05: Carga Masiva con SP (500-1000 Reg.)", ha='center', fontsize=8, style='italic', color='#64748b')

    # UI 3: HITL y Alertas Legales
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    draw_rounded_box(ax, 0.5, 0.5, 9, 11, "", bg_color='#ffffff', border_color='#94a3b8')
    draw_rounded_box(ax, 0.5, 9.8, 9, 1.7, "Pausa de Control y Revisión Humana\nHuman-in-the-Loop (HITL) Activo", bg_color='#b91c1c', border_color='#991b1b', text_color='#ffffff', fontsize=8.5, fontweight='bold')

    draw_rounded_box(ax, 1.0, 6.8, 8.0, 2.5, "⚠ ALERTA LEGAL / NORMATIVA CRÍTICA:\nIncompatibilidad detectada con Ley 32069\nCausa: El expediente carece de estudio de\nsaneamiento físico-legal actualizado.\nAcción requerida: Dictamen de Asesor Jurídico.", bg_color='#fef2f2', border_color='#ef4444', text_color='#991b1b', ha='left', fontsize=7.5, fontweight='bold')

    draw_rounded_box(ax, 1.0, 3.6, 8.0, 2.7, "Checkpoint de Auditoría y Pausa:\n• Estado: PAUSADO POR RIESGO LEGAL\n• Solicitud de Aprobación: Enviada a Gerencia\n• Motivo de intervención registrado en bitácora\n• Firma digital / Hash: 8f4e2b...9a0c", bg_color='#f1f5f9', border_color='#cbd5e1', text_color='#334155', ha='left', fontsize=7.5)

    draw_rounded_box(ax, 1.5, 1.4, 7.0, 0.9, "[ Reanudar con Aprobación ]", bg_color='#dc2626', border_color='#b91c1c', text_color='#ffffff', fontweight='bold', fontsize=8.5)
    ax.text(5, 0.8, "HU-06: Control HITL y Trazabilidad", ha='center', fontsize=8, style='italic', color='#64748b')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_wireframes_pmv2.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 5. MODELO ENTIDAD-RELACIÓN (MER / ERD)
# -------------------------------------------------------------
def generar_modelo_er():
    fig, ax = plt.subplots(figsize=(15, 10.5), dpi=180)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10.5)
    ax.axis('off')

    ax.text(7.5, 10.1, "DISEÑO DEL MODELO ENTIDAD-RELACIÓN (MER) — BASES DE DATOS POSTGRESQL (SIPRIM)",
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0f172a')
    ax.text(7.5, 9.75, "Estructura Lógica y Física de Tablas, Llaves Primarias/Foráneas y Procedimientos Almacenados",
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # ESQUEMA AUTH_DB (Izquierda Superior)
    draw_rounded_box(ax, 0.5, 6.8, 3.8, 2.6,
                     "auth_db.usuarios\n------------------------------------\nPK  id : UUID\n    username : VARCHAR(50)\n    email : VARCHAR(100)\n    password_hash : VARCHAR(255)\n    nombre_completo : VARCHAR(150)\n    activo : BOOLEAN\n    created_at : TIMESTAMP",
                     bg_color='#e0e7ff', border_color='#4338ca', text_color='#1e1b4b', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 0.5, 3.8, 3.8, 2.4,
                     "auth_db.roles_usuario\n------------------------------------\nPK  id : INT\nFK  usuario_id : UUID\n    rol : VARCHAR(30)  -- 'planificador',\n      -- 'asesor_legal', 'gerente', 'auditor'\n    created_at : TIMESTAMP",
                     bg_color='#e0e7ff', border_color='#4338ca', text_color='#1e1b4b', ha='left', fontsize=7.2)
    draw_arrow(ax, 2.4, 6.8, 2.4, 6.2, color='#4338ca')

    # ESQUEMA PLATFORM_DB (Centro y Derecha)
    draw_rounded_box(ax, 5.2, 7.0, 4.4, 2.4,
                     "platform_db.proyectos\n------------------------------------\nPK  id : UUID\n    codigo_cui : VARCHAR(20) UNIQUE\n    nombre : VARCHAR(255)\n    sector : VARCHAR(50)\n    distrito : VARCHAR(50) DEFAULT 'El Tambo'\n    estado : VARCHAR(30)\nFK  creado_por : UUID (auth_db.usuarios)",
                     bg_color='#f0fdf4', border_color='#16a34a', text_color='#14532d', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 5.2, 3.8, 4.4, 2.7,
                     "platform_db.expedientes_versiones\n------------------------------------\nPK  id : UUID\nFK  proyecto_id : UUID\n    numero_version : INT\n    monto_inversion : NUMERIC(14,2)\n    duracion_estimada_dias : INT\n    beneficiarios : INT\n    ruta_documento_tecnico : VARCHAR(255)\n    hash_integridad_sha256 : CHAR(64)\n    created_at : TIMESTAMP",
                     bg_color='#f0fdf4', border_color='#16a34a', text_color='#14532d', ha='left', fontsize=7.2)
    draw_arrow(ax, 7.4, 7.0, 7.4, 6.5, color='#16a34a')

    draw_rounded_box(ax, 10.4, 7.0, 4.1, 2.4,
                     "platform_db.criterios_evaluacion\n------------------------------------\nPK  id : INT\n    codigo : VARCHAR(20)\n    dimension : VARCHAR(30) -- 'economica',\n      -- 'social', 'ambiental', 'legal'\n    peso_ponderado : NUMERIC(5,2)\n    version_config : INT\n    activo : BOOLEAN",
                     bg_color='#fef3c7', border_color='#d97706', text_color='#78350f', ha='left', fontsize=7.2)

    draw_rounded_box(ax, 10.4, 3.8, 4.1, 2.7,
                     "platform_db.evaluaciones_multidim\n------------------------------------\nPK  id : UUID\nFK  expediente_version_id : UUID\n    puntaje_economico : NUMERIC(5,2)\n    puntaje_social : NUMERIC(5,2)\n    puntaje_ambiental : NUMERIC(5,2)\n    puntaje_legal : NUMERIC(5,2)\n    puntaje_global : NUMERIC(5,2)\n    estado_dictamen : VARCHAR(30)\n    created_at : TIMESTAMP",
                     bg_color='#fef3c7', border_color='#d97706', text_color='#78350f', ha='left', fontsize=7.2)
    draw_arrow(ax, 9.6, 5.1, 10.4, 5.1, color='#d97706')

    # TABLA ML Y PROCEDIMIENTOS ALMACENADOS (Abajo Izquierda/Centro)
    draw_rounded_box(ax, 0.5, 0.7, 5.0, 2.6,
                     "platform_db.ml_prediction_logs (U3)\n------------------------------------\nPK  id : UUID\nFK  expediente_id : UUID\n    costo_base : NUMERIC(12,2)\n    plazo_dias : INT\n    sobrecosto_probabilidad : NUMERIC(5,4)\n    sobrecosto_clasificacion : VARCHAR(30)\n    viabilidad_categoria : VARCHAR(40)\n    tiempo_inferencia_ms : NUMERIC(8,3)\n    ejecutado_via_sp : BOOLEAN DEFAULT TRUE",
                     bg_color='#fae8ff', border_color='#c026d3', text_color='#701a75', ha='left', fontsize=7.0)

    draw_rounded_box(ax, 6.0, 0.7, 4.5, 2.6,
                     "platform_db.solicitudes_revision_hitl\n------------------------------------\nPK  id : UUID\nFK  evaluacion_id : UUID\n    tipo_alerta : VARCHAR(50)\n    descripcion_bloqueo : TEXT\n    estado : VARCHAR(30) -- 'PAUSADO',\n      -- 'REANUDADO_APROBADO', 'OBSERVADO'\nFK  revisor_gerente_id : UUID\n    hash_decision : CHAR(64)\n    fecha_decision : TIMESTAMP",
                     bg_color='#fee2e2', border_color='#dc2626', text_color='#7f1d1d', ha='left', fontsize=7.0)

    draw_rounded_box(ax, 11.0, 0.7, 3.5, 2.6,
                     "economic_db.metricas_costo\n------------------------------------\nPK  id : INT\n    sector : VARCHAR(50)\n    costo_m2_promedio : NUMERIC\n    tasa_descuento_social : 0.08\n    fuente : VARCHAR(100)\n    ano_vigencia : INT",
                     bg_color='#e0f2fe', border_color='#0284c7', text_color='#0369a1', ha='left', fontsize=7.0)

    # Flechas de conexión entre tablas
    draw_arrow(ax, 4.3, 8.0, 5.2, 8.0, color='#475569')
    draw_arrow(ax, 5.2, 1.8, 5.5, 4.0, color='#c026d3')
    draw_arrow(ax, 10.4, 4.5, 8.5, 2.5, color='#dc2626')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_modelo_er.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 6. DISEÑO DE PAQUETES UML (ARQUITECTURA HEXAGONAL)
# -------------------------------------------------------------
def generar_paquetes_uml():
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=180)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9.5)
    ax.axis('off')

    ax.text(7.5, 9.1, "DISEÑO DE PAQUETES UML — ARQUITECTURA HEXAGONAL (PORTS & ADAPTERS)",
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0f172a')
    ax.text(7.5, 8.7, "Estructura del Backend FastAPI: Separación de Dominio, Casos de Uso e Infraestructura",
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # CAPA DOMINIO (Centro - Núcleo)
    draw_rounded_box(ax, 4.8, 4.5, 5.4, 3.8, "", bg_color='#eff6ff', border_color='#2563eb', boxstyle="round,pad=0.3,rounding_size=0.1")
    ax.text(7.5, 8.0, "«package» backend.domain (Core)", ha='center', fontsize=9.5, fontweight='bold', color='#1d4ed8')
    
    draw_rounded_box(ax, 5.1, 6.2, 4.8, 1.5,
                     "«entities»\n• Proyecto · ExpedienteTecnico\n• PrediccionML (Sobrecosto / Viabilidad)\n• EvaluacionMultidimensional",
                     bg_color='#ffffff', border_color='#93c5fd', text_color='#1e3a8a', fontsize=7.8)
    
    draw_rounded_box(ax, 5.1, 4.8, 4.8, 1.2,
                     "«ports / interfaces»\n• MLPredictionPort · DatabasePort\n• IAServicePort · AuditoriaPort",
                     bg_color='#ffffff', border_color='#93c5fd', text_color='#1e3a8a', fontsize=7.8)

    # CAPA APLICACIÓN (Izquierda - Casos de Uso y DTOs)
    draw_rounded_box(ax, 0.5, 4.5, 3.8, 3.8, "", bg_color='#f0fdf4', border_color='#16a34a', boxstyle="round,pad=0.3,rounding_size=0.1")
    ax.text(2.4, 8.0, "«package» backend.application", ha='center', fontsize=9.5, fontweight='bold', color='#15803d')

    draw_rounded_box(ax, 0.7, 6.2, 3.4, 1.5,
                     "«use_cases»\n• PredecirMetricasML\n• RegistrarExpediente\n• EvaluarCarteraProyectos",
                     bg_color='#ffffff', border_color='#86efac', text_color='#14532d', fontsize=7.8)

    draw_rounded_box(ax, 0.7, 4.8, 3.4, 1.2,
                     "«dto»\n• MLPredictionInputDTO\n• MLPredictionOutputDTO\n• ExpedienteDTO",
                     bg_color='#ffffff', border_color='#86efac', text_color='#14532d', fontsize=7.8)

    # Flecha Aplicación -> Dominio
    draw_arrow(ax, 4.1, 6.2, 4.8, 6.2, color='#15803d', width=2)
    ax.text(4.45, 6.5, "usa", fontsize=7.5, color='#15803d', ha='center')

    # INFRAESTRUCTURA INBOUND (Controladores - Arriba a la Derecha)
    draw_rounded_box(ax, 10.7, 5.6, 3.8, 2.7, "", bg_color='#faf5ff', border_color='#9333ea', boxstyle="round,pad=0.3,rounding_size=0.1")
    ax.text(12.6, 8.0, "«package» infrastructure.input", ha='center', fontsize=9, fontweight='bold', color='#7e22ce')
    draw_rounded_box(ax, 10.9, 6.0, 3.4, 1.7,
                     "«controllers / routers»\n• MLController (/api/v1/ml)\n• ExpedientesController\n• AuthController",
                     bg_color='#ffffff', border_color='#d8b4fe', text_color='#581c87', fontsize=7.8)

    # Flecha Inbound -> Aplicación
    draw_arrow(ax, 10.7, 7.0, 4.3, 7.5, color='#9333ea', width=1.5)

    # INFRAESTRUCTURA OUTBOUND (Adaptadores - Abajo)
    draw_rounded_box(ax, 0.5, 0.5, 14.0, 3.5, "", bg_color='#f8fafc', border_color='#475569', boxstyle="round,pad=0.3,rounding_size=0.1")
    ax.text(7.5, 3.7, "«package» backend.infrastructure.output (Adaptadores que implementan los Puertos)", ha='center', fontsize=9.5, fontweight='bold', color='#334155')

    draw_rounded_box(ax, 0.8, 0.8, 4.0, 2.5,
                     "«adapter: ML»\nScikitLearnAdapter\n---------------------------\n• Carga joblib de modelos\n• Inferencia Sobrecosto\n• Inferencia Viabilidad\n• Retorna MLPredictionOutput",
                     bg_color='#ffffff', border_color='#cbd5e1', text_color='#0f172a', fontsize=7.5)

    draw_rounded_box(ax, 5.5, 0.8, 4.3, 2.5,
                     "«adapter: Persistence»\nPostgresAdapter & StoredProcedures\n---------------------------\n• sp_registrar_evaluacion_masiva\n• sp_evaluar_expediente_ml\n• Pool asyncpg / SQLAlchemy",
                     bg_color='#ffffff', border_color='#cbd5e1', text_color='#0f172a', fontsize=7.5)

    draw_rounded_box(ax, 10.4, 0.8, 3.8, 2.5,
                     "«adapter: External IA»\nGeminiAdapter (Google AI)\n---------------------------\n• RAG documental normativo\n• Recuperación Ley 32069\n• Análisis de incongruencias",
                     bg_color='#ffffff', border_color='#cbd5e1', text_color='#0f172a', fontsize=7.5)

    # Flechas de implementación hacia los puertos del dominio (Regla de dependencia hexagonal)
    draw_arrow(ax, 2.8, 3.3, 6.0, 4.8, color='#475569', width=1.5, style='->')
    draw_arrow(ax, 7.6, 3.3, 7.6, 4.8, color='#475569', width=1.5, style='->')
    draw_arrow(ax, 12.3, 3.3, 9.2, 4.8, color='#475569', width=1.5, style='->')
    ax.text(7.6, 4.0, "«implements»", ha='center', fontsize=7.5, color='#475569')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_paquetes_uml.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 7. DISEÑO DE DESPLIEGUE CON NODOS UML
# -------------------------------------------------------------
def generar_despliegue_uml():
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=180)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.5)
    ax.axis('off')

    ax.text(7.5, 8.1, "DISEÑO DE DESPLIEGUE CON NODOS UML — SISTEMA SIPRIM",
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0f172a')
    ax.text(7.5, 7.7, "Topología de Nodos Físicos, Nodos de Ejecución, Artefactos y Protocolos de Comunicación",
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # NODO CLIENTE
    draw_rounded_box(ax, 0.5, 4.0, 3.2, 3.2, "", bg_color='#f8fafc', border_color='#334155')
    ax.text(2.1, 6.9, "«device»\nTerminal del Usuario", ha='center', fontsize=8.5, fontweight='bold')
    draw_rounded_box(ax, 0.7, 4.3, 2.8, 2.1,
                     "«execution environment»\nNavegador Web (Chrome/Firefox)\n-----------------------------\n«artifact»\nSIPRIM SPA (React 18 / Vite)\n• TypeScript / TailwindCSS\n• HTML5 LocalStorage",
                     bg_color='#ffffff', border_color='#cbd5e1', text_color='#0f172a', fontsize=7.0)

    # NODO SERVIDOR WEB / FRONTEND HOSTING
    draw_rounded_box(ax, 4.3, 4.0, 3.0, 3.2, "", bg_color='#f0fdf4', border_color='#16a34a')
    ax.text(5.8, 6.9, "«device»\nVercel Cloud / Edge Host", ha='center', fontsize=8.5, fontweight='bold', color='#14532d')
    draw_rounded_box(ax, 4.5, 4.3, 2.6, 2.1,
                     "«execution environment»\nNode.js Static Web Server\n-----------------------------\n«artifact»\nfrontend-dist.bundle\n(Static Assets, CSS, JS 399 kB)",
                     bg_color='#ffffff', border_color='#86efac', text_color='#14532d', fontsize=7.0)

    # NODO SERVIDOR BACKEND API
    draw_rounded_box(ax, 8.0, 4.0, 3.2, 3.2, "", bg_color='#eff6ff', border_color='#2563eb')
    ax.text(9.6, 6.9, "«device / VM Linux»\nServidor Backend API", ha='center', fontsize=8.5, fontweight='bold', color='#1e3a8a')
    draw_rounded_box(ax, 8.2, 4.3, 2.8, 2.1,
                     "«execution environment»\nPython 3.11 Runtime (FastAPI)\n-----------------------------\n«artifact»\nsiprim-backend.asgi (Uvicorn)\n«artifact»\nscikit-learn models (.joblib)\n• sobrecosto_rf.joblib\n• viabilidad_gb.joblib",
                     bg_color='#ffffff', border_color='#93c5fd', text_color='#1e3a8a', fontsize=6.8)

    # NODO BASE DE DATOS
    draw_rounded_box(ax, 11.8, 4.0, 2.8, 3.2, "", bg_color='#fef3c7', border_color='#d97706')
    ax.text(13.2, 6.9, "«device / Container»\nServidor de Base de Datos", ha='center', fontsize=8.5, fontweight='bold', color='#78350f')
    draw_rounded_box(ax, 12.0, 4.3, 2.4, 2.1,
                     "«database system»\nPostgreSQL 18.6 (siprim-pg)\n-----------------------------\n«database»\nplatform_db, auth_db, economic_db\n«artifact»\nStored Procedures (PL/pgSQL)\n• sp_evaluar_masivo",
                     bg_color='#ffffff', border_color='#fde68a', text_color='#78350f', fontsize=6.8)

    # Flechas de conexión entre nodos principales
    draw_arrow(ax, 3.7, 5.5, 4.3, 5.5, color='#334155', width=1.5)
    ax.text(4.0, 5.7, "HTTPS", fontsize=7, color='#334155', ha='center')

    draw_arrow(ax, 3.7, 4.8, 8.0, 4.8, color='#2563eb', width=2)
    ax.text(5.85, 5.0, "HTTPS / REST JSON (CORS)", fontsize=7, color='#2563eb', ha='center')

    draw_arrow(ax, 11.2, 5.5, 11.8, 5.5, color='#d97706', width=2)
    ax.text(11.5, 5.7, "TCP 5432 (asyncpg)", fontsize=6.8, color='#d97706', ha='center')

    # SERVICIOS EXTERNOS (Fila Inferior)
    draw_rounded_box(ax, 2.0, 0.8, 5.0, 2.2, "", bg_color='#fdf4ff', border_color='#c026d3')
    ax.text(4.5, 2.7, "«external system»\nBanco de Inversiones MEF (Invierte.pe)", ha='center', fontsize=8.5, fontweight='bold', color='#701a75')
    ax.text(4.5, 1.6, "Portal de Datos Abiertos Junín / Huancayo\n• Dataset histórico de 1,500 iniciativas\n• Cursos de proyectos de infraestructura\n• Protocolo: API REST / OpenData CSV", ha='center', fontsize=7.2, color='#701a75')

    draw_rounded_box(ax, 8.5, 0.8, 5.0, 2.2, "", bg_color='#fef2f2', border_color='#dc2626')
    ax.text(11.0, 2.7, "«cloud service»\nGoogle Gemini API (Vertex AI)", ha='center', fontsize=8.5, fontweight='bold', color='#991b1b')
    ax.text(11.0, 1.6, "Modelo Gemini 1.5 Flash (RAG Normativo)\n• Extracción de contexto de Ley 32069\n• Análisis de congruencia jurídica\n• Protocolo: HTTPS / gRPC API Key", ha='center', fontsize=7.2, color='#991b1b')

    # Flechas a servicios externos
    draw_arrow(ax, 9.6, 4.0, 4.5, 3.0, color='#c026d3', width=1.5)
    ax.text(6.8, 3.5, "Entrenamiento Offline / Ingesta", fontsize=7, color='#c026d3', ha='center')

    draw_arrow(ax, 10.0, 4.0, 11.0, 3.0, color='#dc2626', width=1.5)
    ax.text(11.1, 3.5, "HTTPS API Key", fontsize=7, color='#dc2626', ha='center')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_despliegue_uml.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 8. EDT / WBS GRÁFICA PARA INGENIERÍA Y GESTIÓN
# -------------------------------------------------------------
def generar_edt_wbs():
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=180)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9.5)
    ax.axis('off')

    ax.text(7.5, 9.1, "ESTRUCTURA DE DESGLOSE DEL TRABAJO (EDT / WBS) — SIPRIM",
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')
    ax.text(7.5, 8.7, "Desglose Jerárquico Orientado a Entregables: Gestión del Proyecto e Ingeniería de Software",
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # NODO RAÍZ (Nivel 1)
    draw_rounded_box(ax, 4.5, 7.5, 6.0, 0.9, "1.0 SISTEMA SIPRIM\n(Sistema Multiagente de Inversión Municipal)", bg_color='#1e293b', border_color='#0f172a', text_color='#ffffff', fontweight='bold', fontsize=9.5)

    # Nodos Nivel 2: 1.1 Gestión vs 1.2 Ingeniería
    draw_rounded_box(ax, 0.8, 5.8, 6.2, 0.9, "1.1 GESTIÓN DEL PROYECTO (Scrum / ICACIT)\nResponsable: Product Owner / Scrum Master", bg_color='#dbeafe', border_color='#1d4ed8', text_color='#1e3a8a', fontweight='bold', fontsize=8.5)
    draw_rounded_box(ax, 8.0, 5.8, 6.2, 0.9, "1.2 INGENIERÍA Y SOFTWARE (PMV1, PMV2, PMV3)\nResponsable: Scrum Team Técnico", bg_color='#dcfce7', border_color='#15803d', text_color='#14532d', fontweight='bold', fontsize=8.5)

    draw_arrow(ax, 6.0, 7.5, 3.9, 6.7, color='#334155', width=1.8)
    draw_arrow(ax, 9.0, 7.5, 11.1, 6.7, color='#334155', width=1.8)

    # Paquetes de Gestión (Nivel 3)
    paquetes_gestion = [
        ("1.1.1 Acta de Constitución\n• Alcance, objetivos, riesgos", 0.5, 4.2),
        ("1.1.2 Gestión de Requisitos\n• Backlog, épicas y HUs", 0.5, 3.0),
        ("1.1.3 Sprints Scrum y Trello\n• Sprints 0 al 5, burndown", 0.5, 1.8),
        ("1.1.4 Juicio de Expertos\n• Validación con Job Gamarra", 0.5, 0.6)
    ]
    for nom, x, y in paquetes_gestion:
        draw_rounded_box(ax, x, y, 6.5, 0.95, nom, bg_color='#eff6ff', border_color='#93c5fd', text_color='#1e3a8a', ha='left', fontsize=7.8)
        draw_arrow(ax, 3.9, 5.8, x + 3.25, y + 0.95, color='#1d4ed8', width=1.2)

    # Paquetes de Ingeniería (Nivel 3)
    paquetes_ing = [
        ("1.2.1 Arquitectura y Modelado\n• Hexagonal, diagramas UML y ERD", 8.0, 4.5),
        ("1.2.2 Base de Datos PostgreSQL\n• auth, platform, economic y SPs", 8.0, 3.4),
        ("1.2.3 Machine Learning (2 Casos)\n• Random Forest y Gradient Boosting", 8.0, 2.3),
        ("1.2.4 Frontend y Visualización\n• React, TypeScript, dashboard y mapa", 8.0, 1.2),
        ("1.2.5 Pruebas y Carga Masiva\n• 243 pytest y 750 transacciones ACID", 8.0, 0.1)
    ]
    for nom, x, y in paquetes_ing:
        draw_rounded_box(ax, x, y, 6.5, 0.95, nom, bg_color='#f0fdf4', border_color='#86efac', text_color='#14532d', ha='left', fontsize=7.8)
        draw_arrow(ax, 11.1, 5.8, x + 3.25, y + 0.95, color='#15803d', width=1.2)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_edt_wbs.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

# -------------------------------------------------------------
# 9. CRONOGRAMA GANTT LÍNEA BASE VS. EJECUCIÓN REAL
# -------------------------------------------------------------
def generar_gantt_cronograma():
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=180)

    actividades = [
        "1.1.1 Acta de Constitución y Chárter",
        "1.1.2 Requisitos y Product Backlog",
        "1.2.1 Arquitectura Hexagonal y Modelado UML",
        "1.2.2 Base de Datos y Procedimientos Almacenados",
        "1.2.3 PMV1: Núcleo Económico y Validación",
        "1.2.4 PMV2: Módulo ML (Sobrecosto y Viabilidad)",
        "1.2.5 PMV2: Carga Masiva Transaccional (750 reg)",
        "1.1.4 Revisión Técnica con Expertos Temáticos",
        "1.2.6 Suite de Pruebas Automatizadas (243 tests)",
        "1.1.5 Sustentación U3 y Entrega Semana 12"
    ]

    # Fechas simuladas en semanas desde semana 1 a semana 12 (Semanas 0 a 12)
    # Formato: (inicio_lb, fin_lb), (inicio_real, fin_real), porcentaje_avance
    datos = [
        ((1, 2), (1, 2.2), 100),
        ((2, 4), (2, 4.5), 100),
        ((3, 5), (3.5, 5.5), 100),
        ((5, 7), (5, 7.2), 100),
        ((6, 8), (6, 8.5), 100),
        ((8, 11), (8.5, 11.5), 100),
        ((10, 11.5), (10, 12), 100),
        ((9, 11), (9.5, 11.8), 100),
        ((10.5, 12), (10.5, 12), 100),
        ((11.5, 12.5), (12, 12.5), 95)
    ]

    y_pos = list(range(len(actividades)))
    y_pos.reverse()

    for idx, (lb, real, pct) in enumerate(datos):
        y = y_pos[idx]
        # Barra Línea Base (Gris / Azul claro)
        ax.barh(y + 0.18, lb[1] - lb[0], left=lb[0], height=0.32, color='#94a3b8', edgecolor='#64748b', label='Línea Base (Plan)' if idx==0 else "")
        # Barra Ejecución Real (Verde si 100%, Ámbar si <100%)
        col = '#10b981' if pct == 100 else '#f59e0b'
        edge = '#047857' if pct == 100 else '#d97706'
        ax.barh(y - 0.18, real[1] - real[0], left=real[0], height=0.32, color=col, edgecolor=edge, label='Ejecución Real' if idx==0 else "")
        # Texto de avance
        ax.text(real[1] + 0.15, y - 0.18, f"{pct}%", va='center', fontsize=8, fontweight='bold', color='#1e293b')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(actividades, fontsize=8.5, fontweight='bold', color='#1e293b')
    ax.set_xlabel("Semanas del Semestre Académico (Semana 1 a Semana 12 - Noviembre 2026)", fontsize=9.5, fontweight='bold', color='#334155')
    ax.set_xlim(0, 13.5)
    ax.set_xticks(range(1, 14))
    ax.set_xticklabels([f"Sem {i}" for i in range(1, 14)], fontsize=8.5)
    ax.grid(axis='x', linestyle='--', alpha=0.6, color='#cbd5e1')
    ax.set_title("CRONOGRAMA GANTT: LÍNEA BASE VS. EJECUCIÓN REAL SEGÚN EDT (SIPRIM U3 S12)", fontsize=11.5, fontweight='bold', color='#0f172a', pad=15)
    ax.legend(loc='lower right', frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1', fontsize=8.5)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diagrama_gantt_cronograma.png")
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Generado: {path}")

if __name__ == '__main__':
    print("Iniciando generación de diagramas para el informe...")
    generar_arbol_problemas()
    generar_flujo_navegacion()
    generar_wireframes_pmv1()
    generar_wireframes_pmv2()
    generar_modelo_er()
    generar_paquetes_uml()
    generar_despliegue_uml()
    generar_edt_wbs()
    generar_gantt_cronograma()
    print("¡Todos los diagramas fueron generados exitosamente!")

