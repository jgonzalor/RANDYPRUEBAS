import streamlit as st

from core.local_store import get_local_payload, has_local_data, is_local_forced
from core.runtime import active_mode

st.set_page_config(
    page_title="ICC Control Territorial",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

mode = active_mode()
with st.sidebar:
    if mode == "LOCAL":
        payload = get_local_payload()
        st.success("🟢 Modo temporal activo")
        st.caption(f"Fuente: {payload.get('filename') or 'Base local'}")
    elif mode == "SUPABASE":
        st.success("🟢 Supabase conectado")
    else:
        st.info("⚪ Sin base activa")

pages = {
    "Inicio": [
        st.Page("pages/00_Dashboard.py", title="Dashboard", icon="🏠", default=True),
    ],
    "Carga y estructura": [
        st.Page("pages/01_Importar_Excel.py", title="Cargar Excel", icon="📥"),
        st.Page("pages/02_Personas.py", title="Personas", icon="👥"),
        st.Page("pages/03_Estructura.py", title="Estructura", icon="🌳"),
        st.Page("pages/09_Captura_y_Edicion.py", title="Captura y edición", icon="✏️"),
    ],
    "Territorio": [
        st.Page("pages/04_Secciones.py", title="Secciones", icon="🧭"),
        st.Page("pages/10_Casillas_y_Responsables.py", title="Casillas y responsables", icon="🗳️"),
        st.Page("pages/11_Pendientes_y_Conflictos.py", title="Pendientes y conflictos", icon="⚠️"),
        st.Page("pages/05_Mapa.py", title="Mapa seccional", icon="🗺️"),
    ],
    "Análisis": [
        st.Page("pages/06_Reportes.py", title="Reportes", icon="📊"),
    ],
    "Administración": [
        st.Page("pages/07_Catalogos.py", title="Catálogos", icon="🗂️"),
        st.Page("pages/08_Importaciones.py", title="Historial de importaciones", icon="🧾"),
    ],
}

pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
