# Original User Request

## Initial Request — 2026-07-29T21:10:23Z

Una exploración técnica para mejorar la calidad y estabilidad de SynthRadar. El objetivo es realizar una limpieza profunda del código backend y establecer una suite de pruebas automáticas robusta, dejando el código listo para producción.

Working directory: /Users/dacritter/.gemini/antigravity/playground/pulsing-perseverance
Integrity mode: development

## Requirements

### R1. Modularización del Backend
Refactorizar `synth_arbitrage.py` para separar claramente las responsabilidades: la extracción de datos (scraping web), la lógica de análisis de negocio (detección de basura, accesorios, cálculo de descuentos) y las operaciones de base de datos. El script original debe seguir siendo el punto de entrada principal.

### R2. Suite de Pruebas Automáticas
Implementar un conjunto de pruebas unitarias exhaustivas utilizando un framework estándar (como `pytest`). Las pruebas deben enfocarse en validar la lógica de `analyze_listing` usando datos simulados (mocks) para garantizar que los filtros anti-basura, la detección de accesorios y el etiquetado de unidades defectuosas funcionen perfectamente sin hacer llamadas de red reales.

### R3. Limpieza de Código y Tipado
Aplicar estándares de calidad de código al backend. Esto incluye añadir type hints de Python (anotaciones de tipos) a las funciones clave y asegurar que el código cumpla con los estándares básicos de estilo.

## Acceptance Criteria

### Calidad y Arquitectura
- [ ] La lógica principal de `analyze_listing` (o sus equivalentes refactorizados) puede ser importada y ejecutada aisladamente sin dependencias de red o de base de datos.
- [ ] El código pasa una verificación de sintaxis sin errores y las funciones principales incluyen docstrings descriptivos.

### Testing (Pruebas Unitarias)
- [ ] Existe un directorio `tests/` o un archivo de pruebas dedicado (ej. `test_synth_arbitrage.py`).
- [ ] La suite de pruebas incluye, como mínimo, tests que verifican el descarte de "Junk Keywords" (ej. manual, case), la correcta identificación de "Accesorios" y el cálculo correcto del margen de ahorro.
- [ ] Ejecutar el comando de pruebas (ej. `pytest test_synth_arbitrage.py`) resulta en un 100% de tests aprobados sin errores de importación.

## Follow-up — 2026-07-29T19:51:08Z

Integrar chollos de B-Stock de Thomann en el flujo principal de SynthRadar. Estos artículos deben ser scrapeados por el backend, categorizados independientemente, e intercalados orgánicamente como "publicidad nativa" entre los anuncios de usuarios en el frontend.

Working directory: /Users/dacritter/.gemini/antigravity/playground/pulsing-perseverance
Integrity mode: development

## Requirements

### R1. Scraping Backend de Thomann
Modificar `synth_arbitrage/scraper.py` para activar y asegurar la extracción de sintetizadores desde la sección de B-Stock de Thomann. Se deben extraer el modelo, URL, precio y la URL de la imagen principal.

### R2. Categorización Diferenciada
En `synth_arbitrage/analysis.py`, los artículos de Thomann B-Stock deben etiquetarse claramente de forma que el frontend pueda diferenciarlos matemáticamente de las oportunidades normales (ej. asignando `Plataforma = "Thomann B-Stock"` o un estado específico). No se debe calcular su "ahorro" basándose en el precio de mercado de segunda mano.

### R3. Inyección Intercalada en Frontend
En `index.html`, la función `fetchData()` debe separar los datos recibidos en dos grupos: Oportunidades normales y Anuncios B-Stock. Al pintar la cuadrícula (`grid`), se deben intercalar de forma forzada: por cada 8 anuncios de usuarios normales, inyectar 1 anuncio de B-Stock. Los anuncios B-Stock deben tener un diseño destacado (como publicidad nativa) para diferenciarse visualmente.

## Acceptance Criteria

### Backend & Pruebas
- [ ] La suite de pruebas (`pytest`) ha sido actualizada y pasa al 100%, incluyendo un test específico que verifica que un anuncio simulado de Thomann B-Stock se etiqueta correctamente y no rompe la lógica de márgenes.
- [ ] El script principal puede ejecutarse de principio a fin sin errores al conectarse a Thomann.

### Frontend
- [ ] El código JavaScript en `index.html` procesa la inyección de anuncios sin errores de sintaxis (console.log limpio).
- [ ] La lógica de inyección garantiza matemáticamente que si hay anuncios B-Stock disponibles, estos se insertan intercalados (ej. en las posiciones 8, 16, 24 del grid).
- [ ] El estilo CSS inyectado para los anuncios B-Stock es visualmente distinto (destacado) frente a las tarjetas de anuncios normales.

