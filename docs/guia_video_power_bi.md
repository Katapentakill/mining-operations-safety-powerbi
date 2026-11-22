# Guía para IAs: construir y grabar un informe de Power BI como código

Notas de trabajo de una sesión con Claude sobre este repositorio (informe PBIP/TMDL/PBIR de seguridad minera con datos de MSHA). Sirven para que otra IA (o persona) no repita los tropiezos. Todo lo que sigue se probó en este equipo (Windows 10, Power BI Desktop 2.159, SQL Server en Docker), salvo lo marcado como «sin verificar».

## 1. Reglas de trabajo de este repo (respétalas)

- **Power BI Desktop nunca queda abierto.** Cierra con «No guardar» y comprueba que no queden `PBIDesktop` ni `msmdsrv`. Un guardado accidental reescribe todos los archivos del proyecto.
- **Nada se publica sin orden expresa** (push, release, video, Service). Los commits son locales, con mensaje en inglés.
- **La Fase 8 está en espera** hasta que el dueño la pida: release `.pbit`, CV/LinkedIn, marcar habilidades «Fuerte», verificar el CI.
- Respuestas al dueño: cortas, en español, empezando por la conclusión.
- Los cambios de seguridad o del sistema los hace el dueño; tú le das los pasos.

## 2. Lo que funcionó con PBIP / TMDL / PBIR

- **El PBIR escrito a mano falla en silencio.** Si no conoces el formato de una propiedad, créala una vez en la interfaz de Desktop, guarda (Ctrl+S), lee el JSON generado y replícalo con scripts. Desktop reescribe los archivos al guardar y no pasa nada.
- **Desktop no recarga en caliente.** Para ver un cambio hecho en disco: cierra sin guardar, borra `.pbi\cache.abf` y `unappliedChanges.json`, abre el `.pbip`, pulsa «Actualizar ahora» y luego «Aplicar cambios».
- **Valida las medidas sin interfaz** conectándote al motor local (`msmdsrv`) con `Microsoft.PowerBI.AdomdClient.dll` (está en la carpeta de Power BI de WindowsApps) y consultando `$SYSTEM.TMSCHEMA_MEASURES` (campos `State` y `ErrorMessage`). Así se descubrió que `by` y `top` son palabras reservadas y no sirven de nombre de variable DAX.
- **Trampas de DAX:** una tabla llamada `Mina` se cita `'Mina'[col]`; `FORMAT(BLANK())` devuelve «» (suma `+ 0`); `ALLSELECTED` dentro de un visual queda limitado por las categorías devueltas, así que para «Top N» usa un **filtro Top N del visual** y no una medida de ranking. Las tarjetas que muestran «(En blanco)» se arreglan con `+ 0` en la medida (así se corrigió `Fatalidades`).
- **Formatos PBIR aprendidos:** navegador de páginas horizontal = `layout.orientation "2D"`; botón de acción con texto ligado a una medida (`objects.text` con `selector.id=default`; `fill` y `outline` con `show:false` y **sin** selector); filtro Top N a nivel de visual con `Subquery`; barras de datos en tablas (`objects.columnFormatting`); mapa claro (`objects.mapStyles mapTheme 'grayscale'`); búsqueda en el segmentador (`objects.general.selfFilterEnabled:true`); segmentador de lista horizontal (`general.orientation 1D`); `page.json.visualInteractions` con `NoFilter` para que un gráfico por año no se reduzca a una barra al elegir un año.
- **Capturas sin interfaz:** Archivo → Exportar → «Exportar a PDF»; el PDF cae en `%LOCALAPPDATA%\Temp\Power BI Desktop\print-job-*\`. Conviértelo a PNG con PyMuPDF.
- **Cuidado con los clics:** Archivo → «Informe en blanco» abre una segunda instancia «Sin título» que hay que cerrar.

## 3. Grabar el informe en video (lo que se hizo y lo que falló)

Pipeline usado: `ffmpeg -f gdigrab` (ffmpeg-static) + un registrador de entrada + montaje con ffmpeg y los sintetizadores de sonido del kit de grabación de CIARA (`Capstone_Ciara_grabaciones/src/sonido.mjs`, `generar-musica.mjs`).

| Problema | Causa | Solución |
|---|---|---|
| El kit CIARA no graba Power BI | Usa Playwright (solo navegadores) | Reutilizar solo su sonido y música; grabar con `gdigrab` |
| `GetAsyncKeyState` no ve los clics de la IA | Los clics inyectados duran milisegundos | Usar un **hook de bajo nivel** (`WH_MOUSE_LL` 14 y `WH_KEYBOARD_LL` 13) en PowerShell con `DoEvents` y escribir JSONL con la hora de cada evento |
| La ventana de Claude salió en el video | Es una ventana normal encima de Power BI | Minimizarla con `ShowWindowAsync(hwnd, 6)` durante la toma y restaurarla (`9`) al final |
| La acción `type` escribe todo de golpe | Inyecta paquetes Unicode (`VK_PACKET`, vk 231) | Para que se vea y suene tecla a tecla, usar `key` letra por letra con una espera de 0,3 s |
| Los tiempos no cuadraban | `gdigrab` descarta fotogramas; la duración del encabezado del `.mkv` no sirve | Sincronizar con **cambios de escena** (`select='gt(scene,0.03)',showinfo`) frente a la hora de cada clic |
| La página tarda ~0,9 s en dibujarse tras un clic | Renderizado de Power BI | Retrasar anillos y sonidos ~0,4 s, recortar esperas, o recorrer las páginas una vez antes de grabar |
| El desplegable del segmentador no se cierra | Es de selección múltiple | Volver a hacer clic en su cabecera (no en un cuadro de texto: entra en modo edición) |
| Las capturas del equipo van un paso atrasadas | Latencia de la captura | Pedir una segunda captura antes de decidir |
| Coordenadas | La captura que ve la IA mide 1456 px de ancho; la pantalla real 1920 | Multiplicar por 1,319 para pasar a píxeles reales |

Montaje (script `componer.mjs`, fuera del repo): recortes con `trim`+`concat`, quitar la barra de tareas con `crop`, anillo naranja animado por clic generado con `geq` (sin imágenes externas) y superpuesto con `overlay`, subtítulos `.srt` quemados con `subtitles` (ES y EN), efectos de clic y teclas sintetizados, música ambiental generada por síntesis en el kit (sin copyright) al 8 %, mezcla con `amix`. Resultado de la primera versión: 2:25, ~18 MB por idioma, volumen medio −37 dB (bajo).

Mejoras pendientes (en el orden en que las haría): grabar la página del informe a pantalla completa, cursor deslizante dibujado en el montaje, precalentar las páginas, subir la música a 12–15 % y normalizar el volumen, y cerrar Power BI desde Archivo → Cerrar.

## 4. Investigación: ¿Power BI Desktop tiene modo presentación / pantalla completa?

**Verificado en este equipo (Power BI Desktop 2.159, versión 26.10):** la pestaña **Ver** solo trae Vista de página, Diseño para móviles, Líneas de cuadrícula, Ajustar a la cuadrícula, Bloquear objetos y los paneles Filtros, Marcadores, Selección, Analizador de rendimiento y Sincronización de segmentaciones. **No hay botón de pantalla completa ni de presentación.** La flecha «^» de la esquina derecha de la cinta cambia a una cinta simplificada de una sola fila (gana alto), pero no oculta nada más. Ctrl+F1 enviado desde la herramienta de automatización no tuvo efecto.

**Lo que dicen las fuentes (contradictorio):**

- Una guía de terceros afirma que existe un botón «Full Screen» en Vista de página; en esta versión no existe: [thebricks.com](https://www.thebricks.com/resources/guide-how-to-view-full-screen-in-power-bi-desktop).
- Los foros de la comunidad dicen que Desktop no tiene modo presentación y piden la función como idea pendiente: [«No presentation mode in Power BI Desktop»](https://community.fabric.microsoft.com/t5/Desktop/No-presentation-mode-in-Power-BI-Desktop/td-p/986856), [«Full Screen Dashboards in Power BI Desktop»](https://community.fabric.microsoft.com/t5/Fabric-Ideas/Full-Screen-Dashboards-in-Power-BI-Desktop/idi-p/4533281).
- La documentación de Microsoft describe pantalla completa y modo de enfoque **en el Power BI Service** (icono Ver → Pantalla completa): [Display content in more detail: focus mode and full screen mode](https://learn.microsoft.com/en-ie/power-bi/consumer/end-user-focus) y [Change the display of a report page](https://learn.microsoft.com/en-us/power-bi/service-focus-mode).

**Conclusión:** en Desktop no hay presentación nativa. Opciones, de mejor a peor:

1. **Grabar en Desktop y recortar al lienzo del informe** (la página mide 1280×720, 16:9): sirve ya, sin publicar nada, y se ve como una presentación. Ocultar paneles, cinta simplificada y «Ajustar a la página» antes de grabar.
2. **Publicar en el Power BI Service y grabar con Ver → Pantalla completa.** Es lo más fiel a lo que verá un revisor en la web, pero publicar sale a internet y requiere cuenta; **no hacerlo sin orden del dueño.**
3. Modo lectura de Desktop: sin verificar en esta versión.

**Sobre qué verá quien revise el proyecto:** el informe no está publicado, así que lo abrirá como PBIP en Desktop o verá las capturas del README. Por eso grabar en Desktop es realista; el modo presentación del Service solo importa si algún día se publica.

## 5. Segunda vía: publicar en el Power BI Service y grabar en Chrome (la que dio el mejor resultado)

Con orden expresa del dueño (21-11-2026) se publicó el informe **en «Mi área de trabajo» (privado)**, no con «Publicar en la Web». Qué se aprendió:

**Publicar desde Desktop**
- «Publicar» obliga a guardar, y guardar reescribe los archivos del proyecto. Se evitó con **Archivo → Guardar como** a una copia en la carpeta temporal (`%TEMP%\pbi_publish\MiningOperationsSafety.pbip`) y publicando desde esa copia; el repositorio no cambió.
- Con el caché borrado el informe abre vacío: pulsar «Actualizar ahora» y esperar ~45 s a que cargue SQL Server (Docker debe estar arriba).
- El inicio de sesión de Desktop y del navegador lo hace el dueño (la IA nunca escribe contraseñas). Un Gmail personal no sirve; sirvió una cuenta de universidad con licencia de Power BI.
- Tras publicar aparecen el informe y el modelo semántico en «Mi área de trabajo». Al cerrar, Desktop pregunta si guardar: **No guardar**, y comprobar que no queden `PBIDesktop` ni `msmdsrv`.

**Grabar en el navegador (Claude in Chrome + ffmpeg `gdigrab`)**
| Problema | Causa | Solución |
|---|---|---|
| No se logra la pantalla completa real del navegador | El clic de la extensión (CDP) no cuenta como gesto de usuario: `requestFullscreen` responde «not granted» y F11 simulado no actuó | Grabar la pantalla y **recortar al lienzo del informe** (`.displayArea`); queda como pantalla completa del informe |
| Salen el banner «Claude empezó a depurar este navegador» y la etiqueta «Claude is working here» | Aparecen mientras la extensión actúa y el banner tarda ~45 s en irse; además encoge la página | **Ejecutar todo el guion con un script dentro de la página** (`tools/video/director_web.js`), sin llamadas de la extensión durante la toma. El script espera a que la página recupere su alto |
| Los clics del script no se ven | Los eventos sintéticos no mueven el cursor real | El script dibuja su propio cursor deslizante y un anillo naranja por clic dentro de la página |
| El guion se congela en la primera escena | `requestAnimationFrame` se pausa si Chrome queda tapado; la ventana de Claude **vuelve al frente al terminar el turno** | Usar `setTimeout`; minimizar la ventana de Claude (`ShowWindowAsync(hwnd,6)`) y **no terminar el turno mientras se graba** (esperar con `Wait-Process -Name ffmpeg`) |
| No se sabe cuándo empieza el video | `gdigrab` no marca la hora real | El script cubre la página de negro 1,3 s al inicio; `blackdetect` sobre el recorte da el instante exacto y se calcula `EPOCA0` (el video va ~0,3 s por delante del registro) |

Qué funciona con eventos sintéticos en el Service: botones del navegador de páginas (`.pageNavigator[role=button]`), segmentador desplegable (`.slicer-dropdown-menu`; la lista es virtual: desplazar `scrollTop` antes de buscar el elemento; volver a pulsar el valor elegido lo quita), barras (`svg rect.bar`) y la **búsqueda del segmentador** (`input.searchInput`: hay uno oculto del Año, elegir el de ancho > 0; hay que enviar keydown/keypress/input/keyup con `keyCode`). El estado de los segmentadores se conserva entre tomas: restablecerlo antes de repetir (Mina y la selección del ranking en Mapa).

**Montaje** (`tools/video/componer_web.mjs`, con el sonido del kit CIARA): recorte `crop=1470:827:124:141` (el lienzo medido por `__D.meta`; se suma la barra del navegador, 121 px sin banner), escala a 1664×936 sobre fondo oscuro de 1920×1080 con banda inferior para subtítulos ES/EN, sonidos de clic y de teclas desde el registro (`tools/video/toma5_events.ejemplo.txt` es un ejemplo del formato), música generada al 13 %. Resultado: 2:12, ~8 MB por idioma, audio medio −33 dB.

## 6. Estado al cierre de esta nota

- Informe rediseñado y subido a GitHub (`main` = `0e5fdc1`).
- Todo lo anterior (corrección de `Fatalidades`, guion, esta guía y `tools/video/`) está en `main`. Release **v1.0.0** con el `.pbit` publicado el 21-11-2026; el repositorio se hizo **público** el 22-11-2026.
- Informe publicado en el área de trabajo **privada** del dueño en el Power BI Service (21-11-2026). No está público ni compartido.
- CI: mientras el repo fue privado, GitHub Actions no arrancaba por un bloqueo de facturación de la cuenta («recent account payments have failed»); no era un error del código.
- Videos locales en `video_local/` (excluida de git): `video_web_es.mp4` y `video_web_en.mp4` (la versión buena, desde el Service) y los `video_es/en.mp4` de la primera prueba en Desktop; todos con sus `.srt`.
- Pendiente (Fase 8, solo si el dueño lo pide): subir el video a README/LinkedIn/CV, `.pbit` como release, marcar habilidades «Fuerte», verificar el CI.
