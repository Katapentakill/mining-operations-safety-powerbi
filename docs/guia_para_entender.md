# Guía para entender el proyecto (para Alexander)

Está escrita en español simple para que puedas explicar el proyecto sin mirar el código. Las cifras son las de la foto de datos del 19-21 de noviembre de 2026; si MSHA actualiza sus archivos, cambian.

## 1. La historia en una frase

> «Tomé los datos abiertos de seguridad minera de EE. UU. (MSHA), me quedé con las 43 minas de Freeport-McMoRan y construí un data warehouse en SQL Server y un informe en Power BI que cuenta cómo han evolucionado accidentes, infracciones y exposición al riesgo desde 2000».

Por qué una sola empresa: para contar **una** historia clara y poder rastrear cada cifra hasta un archivo. Si cambias dos líneas de `config.toml` (el nombre del controlador), el mismo proyecto sirve para otra empresa.

## 2. Qué es MSHA y qué publica

MSHA (*Mine Safety and Health Administration*) es el organismo del Departamento del Trabajo de EE. UU. que fiscaliza las minas. Publica datos abiertos de **todas** las minas del país. Aquí usamos nueve archivos, entre ellos:

- **Mines:** una fila por mina (nombre, estado, coordenadas, controlador actual).
- **Accidents:** un accidente reportado por fila (fecha, gravedad, tipo, parte del cuerpo, si fue contratista).
- **Violations y AssessedViolations:** infracciones y su multa.
- **Inspections:** inspecciones realizadas.
- **MinesProdQuarterly:** horas trabajadas y empleados por mina, área y trimestre (las columnas de producción vienen en cero: **no hay toneladas**).

Los archivos se reemplazan cada viernes y la página no declara una licencia; por eso **los datos no están en el repositorio**: los scripts los descargan.

## 3. Por qué la tasa es «por 200.000 horas»

Si una mina tuvo 20 accidentes y otra 200, ¿cuál es más segura? Depende de cuánta gente trabajó. Para comparar se divide por las horas trabajadas. **200.000 horas** son unos 100 trabajadores a tiempo completo durante un año (100 personas × 40 horas × 50 semanas). Así, una tasa de 2,26 significa «unas 2,3 lesiones por cada 100 trabajadores en un año».

En el proyecto: `casos de lesión del personal propio × 200.000 ÷ horas trabajadas`. Solo cuenta personal propio porque las horas de los contratistas no traen el número de mina (decisión 3) y solo trimestres que tienen horas (el año 2026 está incompleto).

## 4. El modelo en estrella, con un ejemplo

Una **tabla de hechos** guarda eventos; las **dimensiones** los describen. Ejemplo con un accidente:

| Hecho (`fact_accident`) | Dimensiones a las que apunta |
|---|---|
| Un accidente (ejemplo inventado): 12-03-2008, 3 días perdidos | **Fecha** (¿qué día, mes, año?), **Mina** (¿cuál? Morenci), **Grado de lesión** (¿días fuera del trabajo?), **Tipo de accidente**, **Parte del cuerpo**, **Área de trabajo** (superficie, planta…), **Empresa** (¿quién controlaba la mina ese día?) |

Los otros hechos son infracciones (con su multa en la misma fila), inspecciones y horas trabajadas (mina × área × trimestre). Detalle y diagrama: [`docs/data_model.md`](data_model.md).

## 5. El recorrido del dato

1. `01_download_msha.py` descarga los zips (unos 414 MB) a `data/raw`.
2. `02_filter_company.py` se queda con las filas de las 43 minas y escribe CSV.
3. `04_load_sqlserver.py` copia los CSV a tablas de texto (`stg`) con `BULK INSERT` dentro de un contenedor Docker.
4. `dwh.usp_load_all` convierte tipos, traduce al español y arma la estrella (`dwh`), todo en una transacción.
5. Vistas `rpt` (solo lectura, usuario `pbi_reader`): lo único que ve Power BI.
6. El proyecto de Power BI (PBIP) lee las vistas, tiene 74 medidas DAX y 7 páginas.

`python scripts/run_all.py` hace los pasos 1 a 4. Las pruebas (`pytest`) comprueban que los totales cuadren entre origen, almacén y medidas.

## 6. Diez medidas DAX, explicadas línea a línea

Todas están en `powerbi/…SemanticModel/definition/tables/`.

1. **Accidentes** = `COUNTROWS(Accidentes)`: cuenta filas de la tabla de accidentes, ya filtradas por lo que elijas (año, mina…).
2. **Fatalidades** = `CALCULATE(COUNTROWS(Accidentes), GradoLesion[Es fatalidad] = TRUE())`: cuenta accidentes cuyo grado de lesión es «fatalidad».
3. **Casos de lesión (personal propio)** = accidentes con grado que «cuenta como lesión» **y** no contratista.
4. **Tasa de incidencia (por 200.000 h)** = `casos × 200000 ÷ horas`, solo en trimestres con horas. `DIVIDE` evita el error de dividir por cero.
5. **Días perdidos** = `SUM(días perdidos)`: suma una columna, no cuenta filas.
6. **% S&S** = `DIVIDE([Infracciones S&S], [Infracciones])`: la parte de infracciones «significativas y sustanciales».
7. **Multa pagada** = suma del monto pagado; mostrado como `US$`.
8. **Horas trabajadas** = suma de horas del trimestre/mina/área.
9. **Infracciones por 100 h de inspección** = `DIVIDE([Infracciones] × 100, [Horas de inspección])`: cuántas infracciones se encuentran por cada 100 horas que dedican los inspectores.
10. **Δ Accidentes (texto)**: compara con el mismo período del año anterior (`SAMEPERIODLASTYEAR`) y arma el texto «▼ 18,1% vs 2023»; solo se activa si hay **un** año elegido (`HASONEVALUE`).

Ojo con una trampa: la tabla se llama `Mina`, y en DAX `Mina[col]` se confunde con la función `MINA()`; hay que escribir `'Mina'[col]` (decisión 27).

## 7. Límites y decisiones que debes poder defender

- **Una sola empresa** (decisión 24): más simple y trazable; no compara con otras mineras.
- **Sin toneladas:** MSHA las publica en cero o vacías para estas minas; el análisis es de plantilla, seguridad y cumplimiento.
- **Contratistas:** 1.482 accidentes (22,3%) los involucran, pero sus horas no traen mina; la tasa usa solo personal propio.
- **2026 parcial:** accidentes hasta noviembre, horas hasta el tercer trimestre.
- **27 de 43 minas** tienen coordenadas; el resto aparece en la tabla pero no en el mapa.
- **Dueños anteriores:** las minas pasaron por Phelps Dodge, Cyprus Amax y otros; por eso hay una dimensión Empresa y una marca «era del dueño actual».
- **Traducción:** los textos de MSHA se traducen en SQL, no visual por visual; el original queda en columnas ocultas (decisión 25).
- **Mapa nativo:** usa el visual de mapa de Power BI (Bing); requiere activar la opción de seguridad de mapas en Desktop (decisión 22). Si no está activada, no se ve.

## 8. Preguntas de entrevista (y cómo responder)

1. **¿Por qué una sola empresa?** Para contar una historia trazable; el código admite otra empresa cambiando `config.toml`.
2. **¿Qué es la tasa por 200.000 horas?** Lesiones por cada 100 trabajadores a tiempo completo en un año; permite comparar minas de distinto tamaño.
3. **¿Por qué excluiste a los contratistas de la tasa?** Sus horas no traen mina, así que dividir sería inconsistente; los muestro aparte (22,3% de los accidentes).
4. **¿Cómo sabes que las cifras están bien?** Pruebas SQL que reconcilian origen, almacén y medidas, y una validación del proyecto de Power BI; las corro en local. El workflow de GitHub Actions las correría en cada cambio, pero hoy GitHub no lo ejecuta por un bloqueo de facturación de mi cuenta.
5. **¿Por qué modelo en estrella?** Es simple de consultar, rápido y deja que Power BI filtre por dimensiones compartidas.
6. **¿Qué es una dimensión «basura»?** Agrupa atributos pocos y repetidos (negligencia, probabilidad…) en una tabla para no ensanchar el hecho.
7. **¿Por qué Docker y `BULK INSERT`?** Reproducibilidad: cualquiera levanta el mismo SQL Server con tres comandos y carga millones de filas rápido.
8. **¿Qué hiciste con los textos en inglés?** Los traduje en el ETL (columnas `*_es`) y conservé el original; los DAX que filtran por valores de MSHA usan la columna original.
9. **¿Por qué el mapa es nativo y qué cuidado tiene?** Muestra burbujas sobre un mapa real con zoom; hay que filtrar a las minas con coordenadas (si no, las sin coordenadas caen en 0,0) y el administrador debe permitir los visuales de mapa.
10. **¿Cómo manejas el año parcial?** Las tasas usan solo trimestres con horas (`has_hours_data`), y la comparación contra el año anterior usa el mismo período.
11. **¿Cómo versionas Power BI?** Como código: PBIP con TMDL y PBIR, revisable en Git; un validador comprueba que cada columna y medida citada exista.
12. **¿Qué mejorarías?** Incluir toneladas si hubiera fuente, comparar contra otras empresas y agregar minigráficos en las tarjetas y un parámetro de campo para cambiar entre tipo y parte del cuerpo (están en el prototipo HTML; el tooltip de página y el drill-through los probé y no funcionaron en Desktop).
13. **Los títulos del informe ¿son texto fijo?** No: son medidas (`Título Resumen`, etc.) que se recalculan con el año y la mina elegidos; se muestran en un botón sin borde porque un cuadro de texto no se enlaza a datos (decisión 29).

## 9. Glosario

- **S&S (significativa y sustancial):** infracción que el inspector considera con probabilidad razonable de causar una lesión grave.
- **CFR:** *Code of Federal Regulations*; el título 30 contiene las normas mineras (por ejemplo 56.20003 = orden y limpieza en minas de superficie metálicas).
- **Tiempo perdido (*lost time*):** lesión con días fuera del trabajo, incapacidad permanente o fatalidad.
- **Incidencia:** casos por 200.000 horas trabajadas.
- **Controlador:** la empresa matriz de una mina en un momento dado.
- **PBIP / TMDL / PBIR:** formato de proyecto de Power BI como archivos de texto (modelo y reporte).
- **ETL:** extraer, transformar y cargar.
- **Dimensión / hecho:** tabla que describe / tabla que registra eventos.
