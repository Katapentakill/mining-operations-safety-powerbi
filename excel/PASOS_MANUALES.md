# Pasos hechos a mano en Excel para la web

El libro base (`python excel/build_excel.py`) trae todo lo que se puede generar por código. Las tablas dinámicas, los segmentadores y el gráfico dinámico no se pueden crear desde código de forma confiable, así que se agregan dentro de Excel. Estos fueron los pasos (Excel para la web, cuenta de la universidad, 22-11-2026).

## 1. Subir el libro base
1. Entrar a `excel.cloud.microsoft` e iniciar sesión.
2. **Cargar un archivo** y elegir `MiningSafety_Excel_base.xlsx` (se abre solo en el navegador).

## 2. Primera tabla dinámica (por mina)
1. Hoja **Pivote**, seleccionar la celda `B6`.
2. **Insertar > Tabla dinámica**; en *Tabla o rango* escribir `t_anio_mina`; ubicación: hoja existente `Pivote!$B$6`; Aceptar.
3. En el panel de campos marcar **Mina** (filas) y **Accidentes**, **Infracciones**, **Multa pagada** (valores). Esperar un par de segundos entre clics: si se hacen muy rápido, alguno no se registra.
4. Comprobar los totales: 6.654 accidentes, 19.046 infracciones, 12.223.998 de multa.

## 3. Segmentadores
1. Con una celda de la tabla dinámica seleccionada: **Insertar > Segmentación**.
2. Marcar **Década** y **Situación** (desplazar la lista para ver la segunda) y Aceptar.
3. Arrastrar los segmentadores para que no se superpongan. Probar: elegir *Activa* deja las 10 minas activas (6.504 accidentes); el icono del embudo borra el filtro.

## 4. Segunda tabla dinámica (por década) y gráfico dinámico
1. Seleccionar `L6`, **Insertar > Tabla dinámica**, `t_anio_mina`, ubicación `Pivote!$L$6`.
2. Marcar **Década** (filas) y **Fatalidades**, **Accidentes**, **Infracciones** (valores). Totales: 15, 6.654 y 19.046.
3. Con una celda de esa tabla seleccionada: **Insertar > Columnas agrupadas**. Se crea un gráfico dinámico; moverlo debajo de la tabla y ponerle título («Fatalidades, accidentes e infracciones por década») desde el panel *Aplicar formato*.

## 5. Descargar
**Archivo > Crear una copia > Descargar una copia**. El archivo conserva: 2 tablas dinámicas, 2 segmentadores, 5 gráficos (4 del panel + el dinámico), 43 minigráficos, barras de datos, listas desplegables y los valores calculados (se verificó leyendo el `.xlsx`).

## Lo que no se pudo: Power Query
En esta cuenta, la pestaña **Datos** de Excel para la web no muestra *Obtener datos* ni *Transformar datos*, y el panel **Consultas y conexiones** dice «0 consultas» sin opción de crear una. Power Query solo se puede crear en Excel de escritorio; por eso el libro y el CV no lo declaran.

## Consejos para quien automatice esto con un navegador
- El botón *Cargar un archivo* abre el selector de archivos de Windows, que no se puede manejar. Se evita impidiendo que el clic abra el selector (escuchar el clic en el `input[type=file]` y llamar a `preventDefault`) y adjuntando el archivo al `input` con la herramienta de carga de archivos.
- Las capturas de pantalla de una herramienta de control del escritorio pueden minimizar Chrome y congelar las capturas del navegador; usar solo las del propio navegador.
