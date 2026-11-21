# Primera apertura en Power BI Desktop (guía para ti)

El modelo y el informe base están escritos como código y **no se han abierto nunca en Power BI Desktop**. Esta es la primera validación real. Si algo falla, copia el mensaje de error exacto y el nombre del archivo que menciona.

## Antes de abrir

1. Docker Desktop encendido y la base cargada: `docker compose up -d --wait` y `python scripts/run_all.py --skip-download`.
2. En tu archivo `.env` está la contraseña `PBI_READER_PASSWORD` (usuario `pbi_reader`).

## Abrir el proyecto

1. Doble clic en `powerbi/MiningOperationsSafety.pbip`.
2. Si pide activar una característica en vista previa (PBIP o TMDL), actívala en *Archivo → Opciones → Características en vista previa* y reinicia.
3. En *Transformar datos → Editar parámetros* deja `Servidor = 127.0.0.1,1433` y `Base = MiningOpsSafety`. No uses `localhost`: Power BI lo resuelve a las IP de red del equipo, donde el contenedor no escucha, y la actualización se queda en "Evaluando…" sin pedir credenciales.
4. Cuando pida credenciales: tipo **Base de datos**, usuario `pbi_reader`, la contraseña de `.env`. Si da error de certificado, desmarca *Cifrar conexiones*.
5. **Actualizar**. Deberían cargar 19 tablas.

## Qué comprobar

| Comprobación | Resultado esperado |
|---|---|
| Vista de modelo | 24 relaciones, todas de muchos a uno hacia las dimensiones |
| Tabla `Fecha` | Marcada como tabla de fechas |
| Página *Resumen* | 4 tarjetas y 3 gráficos con datos |
| Tarjeta *Accidentes* | 6.654 (sin filtros) |
| Tasa de incidencia 2024 | 2,26 |

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| No abre el proyecto o dice que un archivo no es válido | Envíame el mensaje y la ruta del archivo |
| Error al leer una tabla | Revisa que el contenedor está sano: `docker compose ps` |
| Un gráfico sale vacío o con un error de campo | Tal vez el nombre de un campo cambió; envíame el nombre del gráfico |
| Mensaje de que faltan características | Activa la vista previa indicada en el paso 2 |

## Después

- El tema `CopperMining` ya viene aplicado (está registrado en el informe). Las 6 páginas traen barra lateral con navegación (Ctrl+clic en Desktop), cabecera, filtro de año sincronizado y sus visuales.
- Al **guardar como proyecto PBIP**, los cambios quedan en los archivos de texto y Git los muestra (Desktop reescribe el modelo completo, así que revisa el diff antes de comitear).
- Si editas los archivos de `powerbi/` con Desktop abierto, ciérralo con **No guardar** y vuelve a abrir el `.pbip` (Desktop no recarga solo); luego *Actualizar* para ver los datos.
- Anota lo estético pendiente en `docs/pendientes_esteticos.md`.
