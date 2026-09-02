# ICC Control Territorial V2.1

Plataforma independiente para consolidar estructura territorial desde Excel, reconstruir dependencia jerárquica, enriquecer automáticamente la información electoral por **sección**, visualizar cobertura sobre un mapa poligonal de Sinaloa y organizar casillas/responsables.

## Qué cambia en V2

- Cartografía seccional de Sinaloa **precargada** dentro del proyecto.
- 3,855 polígonos disponibles en el archivo cartográfico aportado para esta versión.
- Catálogo territorial precargado con municipio, distrito local, distrito federal, tipo de sección y centroides.
- La **SECCIÓN** funciona como llave para autocompletar territorio sin inventar.
- Conserva `municipio_excel` y registra el origen de los datos derivados.
- Detecta contradicciones entre el Excel y la cartografía.
- Mapa poligonal operativo sin pedir GeoJSON al usuario.
- Carga múltiple de Excel y consolidación temporal.
- Detección de conflictos entre archivos.
- Centro de `Pendientes y conflictos`.
- Módulo de casillas y responsables.
- Descarga automática opcional del catálogo histórico público IEES 2024 para pruebas.
- El catálogo histórico se etiqueta como `HISTORICO_REFERENCIA`; no se presenta como vigente.
- Cuando exista un catálogo nuevo de INE/IEES, puede sustituirse sin borrar personas, jerarquía ni secciones.

## Flujo recomendado para probar

1. Sube el repositorio a Streamlit Cloud y ejecuta `app.py`.
2. En **Cargar Excel**, sube el archivo de Randy.
3. Deja activada la opción de precargar el catálogo histórico IEES 2024 si quieres probar casillas.
4. Activa/acumula el archivo.
5. Recorre:
   - Dashboard
   - Personas
   - Estructura
   - Secciones
   - Casillas y responsables
   - Pendientes y conflictos
   - Mapa seccional
   - Reportes
6. Puedes cargar más Excel y acumularlos en la misma sesión.

## Cartografía

La versión incluye:

- `data/cartografia/secciones_catalogo.csv`
- `data/cartografia/secciones_sinaloa.geojson.gz`
- `data/cartografia/fuente_cartografia.json`

La capa original fue transformada de UTM a WGS84 y simplificada para que Streamlit pueda mostrarla con rapidez. La fuente y la transformación quedan documentadas.

### Regla de enriquecimiento

Si el Excel contiene:

```text
SECCION = 316
```

V2 puede derivar, cuando la sección existe en la cartografía precargada:

```text
Municipio
Distrito Local
Distrito Federal
Tipo de sección
Centroide
```

El sistema conserva el municipio original del Excel. Si hay contradicción, marca el registro `REVISAR` y crea una incidencia; no borra el dato fuente.

## Casillas

V2 distingue entre:

- **inventario de casillas** de una sección;
- **casilla exacta asignada a una persona**;
- **responsable formal** de sección/casilla;
- **coordinador con mayor estructura registrada**.

Una persona se asigna automáticamente a casilla solamente cuando existe evidencia suficiente:

- casilla explícita en el Excel;
- única casilla disponible en la sección;
- rango alfabético oficial suficiente;
- localidad compatible con una extraordinaria y sin ambigüedad.

Si una sección tiene varias casillas y el catálogo histórico no contiene rangos alfabéticos, V2 mantiene `PENDIENTE` en vez de repartir personas artificialmente.

## Catálogo histórico IEES 2024

La aplicación puede intentar descargar el archivo público de Padrón Electoral/Lista Nominal por casilla del IEES Sinaloa. Este catálogo se usa para **pruebas** y queda etiquetado como histórico.

Si la descarga automática falla, puedes descargar el Excel por tu cuenta y cargarlo en **Catálogos → Cargar/actualizar casillas**.

## Supabase

Para explorar V2, Supabase sigue siendo opcional. El modo temporal permite probar la lógica completa durante la sesión.

Para una base existente V1.x, ejecuta:

```text
sql/004_upgrade_v2.sql
```

Para una instalación nueva puedes ejecutar:

```text
sql/001_schema.sql
```

La migración V2 agrega distrito federal, tipo de sección, metadatos de catálogos de casillas y campos adicionales de casilla.

## Secrets

```toml
SUPABASE_URL = "..."
SUPABASE_SERVICE_ROLE_KEY = "..."
```

No incluyas credenciales en el repositorio.

## Pruebas

```bash
pytest -q
```

La V2 incluye pruebas de normalización, jerarquía, casillas, cartografía, enriquecimiento territorial y lectura de catálogo histórico.


## Ajustes V2.1

- Mapa principal con contornos limpios por defecto y color bajo demanda.
- Tooltip operativo con desglose de promovidos por casilla.
- Responsables separados del foco visual principal del mapa.


## Ajustes V2.1.4

- Ficha lateral del mapa rediseñada para mejor lectura.
- Hover con promovidos por casilla y valores en 0 cuando existe catálogo sin asignación.
- Desglose por casilla persistente en la ficha lateral aunque no haya promovidos en alguna casilla.
