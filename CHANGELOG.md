# Changelog

## V2.1.4

- Ficha lateral del mapa rediseñada para una lectura más ejecutiva y agradable.
- El detalle de sección recupera más contexto operativo: ubicación, tipo, métricas y mayor estructura.
- El hover del mapa ahora muestra también promovidos por casilla; cuando una casilla no tiene promovidos se muestra en 0.
- El desglose por casilla ya no desaparece si existe catálogo de casillas pero no hay promovidos asignados; se muestran las casillas de la sección con valor 0.
- Mejora en el resumen por casilla tanto para modo temporal/local como para modo Supabase.

## V2.1.3

- El tooltip del mapa se simplifica para no tapar la cartografía.
- Clic sobre una sección abre una ficha operativa fija al costado del mapa.
- La ficha incluye municipio, distrito local, distrito federal, tipo, promovidos, coordinadores, mayor estructura y desglose por casilla.
- Los responsables continúan fuera del foco visual principal del mapa.
- El mapa conserva la regla V2.1.2: secciones con información coloreadas; secciones sin información transparentes con contorno.
- Área operativa del mapa y panel de detalle distribuidos en una vista ancha.

## V2.1.2

- El mapa colorea automáticamente solo las secciones que tienen registros.
- Las secciones sin información quedan sin relleno, conservando únicamente el contorno.
- Se elimina el toggle manual de coloración para que el comportamiento sea operativo por defecto.
- Se mantiene intensidad visual según la métrica seleccionada y resaltado al pasar/seleccionar una sección.

## V2.1.1

- Hotfix del mapa: evita `KeyError` cuando el resumen de casillas no incluye `tipo_casilla`.
- El desglose de casillas ahora ordena únicamente por columnas realmente disponibles.
- Compatible con catálogos históricos y resúmenes temporales con esquemas parciales.

## V2.1.0

- Mapa seccional con visualización operativa priorizada: vista estatal por contornos limpios y sin relleno invasivo por defecto.
- El color por intensidad ahora se activa de forma explícita o al trabajar con filtros territoriales.
- Área de trabajo del mapa ampliada para mejorar navegación, zoom y selección de secciones.
- El reporte emergente del mapa ahora incluye desglose de promovidos por casilla dentro de la sección.
- En la visualización principal se separa el tema de responsables para no dominar la lectura operativa.
- Se mantiene el análisis de responsables en módulos dedicados, dejando el mapa enfocado en cobertura, coordinadores y avance territorial.

## V2.0.0

- Cartografía de Sinaloa precargada dentro del proyecto.
- 3,855 polígonos de sección transformados a WGS84 para el mapa.
- Enriquecimiento automático por sección: municipio, distrito local, distrito federal, tipo de sección y centroide.
- Trazabilidad de municipio capturado vs municipio derivado.
- Incidencias por sección no localizada y conflicto territorial.
- Mapa poligonal listo sin carga manual de GeoJSON.
- Secciones muestra el universo cartográfico, incluso las que no tienen registros.
- Dashboard con cobertura de secciones y distritos.
- Reportes enriquecidos con distritos local/federal.
- Carga múltiple conserva archivo/estructura de origen.
- Detección de conflictos entre archivos: persona repetida, superior distinto, múltiples secciones y teléfono compartido.
- Nuevo Centro de Pendientes y Conflictos.
- Catálogo histórico IEES 2024 descargable automáticamente como referencia para pruebas.
- Catálogos de casilla versionables por proceso/estatus.
- Responsable formal separado del coordinador con mayor estructura.
- Migración Supabase `004_upgrade_v2.sql`.
- 12 pruebas automatizadas.

## V1.3.0

- Carga múltiple de Excel.
- Casillas y responsabilidades territoriales.
- Mapa preparado para GeoJSON.
- Ranking de coordinadores por promovidos.
