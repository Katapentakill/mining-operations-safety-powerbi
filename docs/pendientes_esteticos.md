# Pendientes estéticos (para ti)

Lo funcional está primero; esto es lo que quedó sin pulir a propósito.

- [x] Aplicar el tema `CopperMining` (vive en `powerbi/MiningOperationsSafety.Report/StaticResources/RegisteredResources/` y está registrado en `report.json`).
- [x] Barra superior común con marca, navegador y filtro de año; el título de cada página es una medida (decisión 29). Falta el logo (`assets/logo_placeholder.svg`).
- [x] Nota "proyecto independiente, sin afiliación" en la página «Acerca de los datos». Si usas logos oficiales (Freeport-McMoRan, MSHA), ojo: son marcas o sellos con restricciones de uso.
- [x] Navegación entre las 7 páginas: *Navegador de páginas* horizontal en la barra superior (en Desktop se navega con Ctrl+clic).
- [x] Construir los visuales de las páginas 2 a 6 (mapa de minas como dispersión, porque Desktop trae los mapas desactivados).
- [x] Alinear y dimensionar los visuales de *Resumen*; títulos y etiquetas en español.
- [x] Filtro de año en todas las páginas, sincronizado; los gráficos por año conservan la serie completa.
- [x] Textos en inglés de MSHA traducidos en el data warehouse (decisión 25).
- [x] Página «Acerca de los datos» con insignias propias (sin logos oficiales) y mapa nativo de Power BI (requiere activar los visuales de mapa).
- [x] Texto alternativo en cada visual y orden de tabulación lógico.
- [x] Tarjetas con variación vs año anterior, «cómo leerla» y dato clave por página; página «Detalle por mina».
- [ ] Revisar el contraste final (≥ 4,5:1) con las capturas definitivas (Fase 6).
- [x] Capturas en `docs/img/` enlazadas en el README (se vuelven a tomar si cambia el diseño).
- [x] Capturas nítidas (PDF a PNG) en `docs/img/`.
- [x] README con «Qué cuenta el informe» y `docs/guia_para_entender.md`.
- [ ] Grabar el video corto (guion actualizado en `docs/video_guion.md`) y enlazarlo en el README: lo graba Alexander y solo se publica cuando él lo decida.
- [ ] Pendiente probado y descartado: tooltip de página y drill-through no funcionaron en Desktop (decisión 28).
- [x] Rediseño aprobado portado a Power BI: grupos de gravedad, Top 5, barra 100% de áreas, barras de datos, mapa gris claro, ficha de la mina, búsqueda en el filtro de mina.
- [ ] Minigráficos dentro de las tarjetas, parámetro de campo Tipo / Parte del cuerpo, línea de promedio en el combo y resaltar el año elegido dentro de las tendencias (están en el prototipo; en Power BI requieren visuales extra).
