# Guion del video (2 a 3 minutos, en español)

Grábalo con Xbox Game Bar (Win + G) u OBS, con tu voz, y súbelo a YouTube como *no listado* **solo cuando decidas publicarlo**. Enlázalo en el README, en LinkedIn y en el CV.

Antes de grabar: abre el informe con la base cargada, año = Todas, y cierra el aviso amarillo de Power BI.

| Tiempo | Qué muestras | Qué dices |
|---|---|---|
| 0:00 a 0:20 | Página *Acerca de los datos* | "Analicé datos reales de seguridad minera: la fuente es MSHA, el regulador de EE. UU., y las minas son las 43 de Freeport-McMoRan, entre 2000 y 2026." |
| 0:20 a 0:50 | Página *Resumen* | "Seis cifras cuentan el panorama: 6.654 accidentes, 19.046 infracciones y una tasa de incidencia que cayó de 3,6 en 2008 a 1,9 en 2009." Cambia el año a 2024 y señala la variación contra 2023. |
| 0:50 a 1:20 | Páginas *Accidentes* e *Infracciones y multas* | Un hallazgo: 15 fatalidades desde 2000, o que una de cada cinco infracciones es significativa y sustancial. |
| 1:20 a 1:50 | Página *Mapa y detalle por mina* | "Morenci concentra el 44% de los accidentes." Muestra el mapa, el top 10 y luego *Detalle por mina* con el filtro Mina. |
| 1:50 a 2:15 | Repositorio: README, `docs/data_model.md` y el diagrama del flujo | "Es reproducible: descarga los datos de MSHA, los carga en SQL Server con Docker, los modela en estrella y los muestra en Power BI como código (PBIP y TMDL)." |
| 2:15 a 2:40 | `docs/decisions.md` y una medida DAX (tasa de incidencia) | "Excluí a los contratistas porque no tengo sus horas, y no hay toneladas: lo dejé documentado." |
| 2:40 a 3:00 | Pestaña *Actions* (CI) y `pytest` | "Tiene pruebas automáticas y CI: cuadran los totales entre el origen y el modelo." |

Consejo: no leas el guion; practica una vez y háblalo con tus palabras.
