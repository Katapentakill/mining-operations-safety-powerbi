# Herramientas del video del informe

Scripts usados para grabar y montar el video del informe publicado en el Power BI Service. El detalle y los problemas encontrados están en `docs/guia_video_power_bi.md` (sección 5).

- `director_web.js`: se pega en la página del informe y recorre el guion dentro de la página (cursor, anillos, registro de tiempos). Lanzar con `setTimeout(()=>window.__D.run2(),500)`.
- `componer_web.mjs`: monta el video (recorte al lienzo, sonidos, música, subtítulos ES/EN). Necesita las piezas `src/sonido.mjs` y `src/config.mjs` del kit de grabaciones de CIARA (no incluidas aquí) y ffmpeg.
- `toma5_events.ejemplo.txt`: ejemplo del registro (`época_ms|tipo|x|y|etiqueta`) que lee el montaje.

Los videos (`.mp4`) no van al repositorio.
