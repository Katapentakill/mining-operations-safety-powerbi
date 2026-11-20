# Guion del video (2 a 3 minutos, en español)

Grábalo con Xbox Game Bar (Win + G) u OBS, con tu voz, y súbelo a YouTube como *no listado*. Enlázalo en el README, en LinkedIn y en el CV.

| Tiempo | Qué muestras | Qué dices |
|---|---|---|
| 0:00 a 0:15 | Página *Resumen* | "Analicé datos reales de seguridad minera de 43 minas de cobre de una sola empresa, entre 2000 y 2026." |
| 0:15 a 0:45 | Repositorio en GitHub: README y diagrama del flujo | "Es un proyecto reproducible: descarga los datos públicos de MSHA, los carga en SQL Server con Docker y los muestra en Power BI." |
| 0:45 a 1:15 | `docs/data_model.md` y vista de modelo de Power BI | "El modelo es una estrella: hechos de accidentes, infracciones, inspecciones y horas trabajadas, con dimensiones de fecha, mina y empresa." |
| 1:15 a 1:50 | Páginas *Accidentes* e *Infracciones y multas* | Explica un hallazgo concreto: por ejemplo, la tasa por 200.000 horas por año o el porcentaje de infracciones significativas y sustanciales. |
| 1:50 a 2:15 | Una medida DAX (tasa de incidencia) y `docs/decisions.md` | "Excluí a los contratistas porque no tengo sus horas, y no hay producción en toneladas: lo dejé documentado." |
| 2:15 a 2:40 | Pestaña *Actions* con CI en verde y `pytest` | "Tiene pruebas automáticas y CI: cuadran los totales entre los datos de origen y el modelo." |
| 2:40 a 3:00 | README, sección de inicio rápido | "Con tres comandos cualquiera puede reproducirlo." |

Consejo: no leas el guion; practica una vez y háblalo con tus palabras.
