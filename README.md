# 📊 Contratos Diff - QA & Analytics Audit Tool

Herramienta de auditoría y calidad de datos diseñada para verificar automáticamente que los eventos de telemetría y analíticas emitidos por la aplicación móvil (iOS / Android) coincidan con los **contratos de seguimiento (tracking contracts)** definidos por el equipo de Producto y Analytics.

---

### 🎯 Objetivo de Negocio

En entornos de alto impacto, la precisión de las métricas en plataformas de analítica como **CleverTap** es crítica para la toma de decisiones, la segmentación de usuarios y la atribución de conversiones. 

Un cambio de nombre de parámetro, una propiedad faltante o un formato de fecha incorrecto en una actualización de la app puede romper embudos de conversión o reportes de negocio sin ser detectado a simple vista.

Esta herramienta automatiza esa validación comparando las capturas reales de CleverTap con los esquemas esperados, garantizando:

* **Gobierno de datos e integridad:** Asegura que los eventos de compras, búsquedas y reembolsos lleguen completos a CleverTap.
* **Reducción de tiempos de QA:** Evita revisiones manuales campo por campo al generar un reporte visual con discrepancias marcadas en colores.
* **Detección temprana de regresiones:** Identifica si una nueva versión de la app omitió atributos clave (`ifv`, `abckt`, IDs de transacciones, etc.).

---

### 🔍 ¿Qué Analiza y Detecta?

El script genera un reporte visual comparativo (*side-by-side*) que analiza y resalta:

| Indicador | Significado de Negocio |
| :--- | :--- |
| **❌ Campo Faltante (Rojo)** | Propiedades exigidas por el contrato de seguimiento que la app **no envió** a CleverTap (riesgo de pérdida de datos). |
| **🔵 Valor / Formato Distinto (Azul)** | Propiedades presentes pero cuyos valores difieren del parámetro esperado o de los formatos de fecha exigidos (ej. formato timestamp CleverTap `$D_`). |
| **🟢 Campo Adicional (Verde)** | Atributos adicionales enviados por la aplicación que no estaban contemplados en el contrato base. |

---

### ⚙️ Flujo de Funcionamiento

1. **Entrada de Datos:**
   * `contracts-ios.zip`: Archivos `.json` que definen la estructura esperada para cada evento (`Charged`, `click_purchase_detail_continue`, `search_status`, etc.).
   * **Reporte Base (HTML):** Exportación o captura de eventos de CleverTap para un usuario particular.
2. **Procesamiento (`generate.py`):**
   * Descomprime y normaliza los esquemas de contratos.
   * Asocia dinámicamente el contexto del flujo (ej. Búsquedas *RoundTrip* vs *OneWay*, Reembolsos de *Ida* vs *Vuelta*).
   * Mapea y compara jerárquicamente cada objeto JSON.
3. **Salida:**
   * Genera un reporte HTML auto-contenido dentro de la carpeta `generated-diff/` nombrado con fecha y hora: `generated-diff/Reporte_Contratos_YYYYMMDDHHMMSS.html`.

---

### 🚀 Requisitos e Instalación

**Prerrequisitos:**
* Python 3.8 o superior.

**Estructura esperada del proyecto:**

```text
contratos-diff/
├── generate.py                     # Script principal de comparación
├── contracts-ios.zip               # ZIP con los esquemas JSON esperados
├── Reporte_Contratos_XXXXXX.html   # Reporte HTML exportado de CleverTap
├── generated-diff/                 # (Se crea automáticamente) Reportes de salida
└── .gitignore