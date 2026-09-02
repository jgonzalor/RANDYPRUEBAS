import pandas as pd
import streamlit as st

from core.cartography import source_metadata
from core.local_store import build_demo_dataset, get_local_booth_catalog_meta, get_local_payload, get_local_sections, local_dashboard_metrics
from core.queries import dashboard_metrics
from core.runtime import active_mode, optional_client

st.title("ICC Control Territorial V2")
st.caption("Estructura, cobertura seccional, cartografía precargada, casillas y responsables territoriales")
mode = active_mode()

if mode == "EMPTY":
    st.info("Puedes explorar sin Supabase: carga uno o varios Excel o activa el demo.")
    c1, c2 = st.columns(2)
    c1.page_link("pages/01_Importar_Excel.py", label="📥 Cargar Excel", use_container_width=True)
    if c2.button("🧪 Activar demo", type="primary", use_container_width=True):
        build_demo_dataset(); st.rerun()
    st.stop()

if mode == "LOCAL":
    p = get_local_payload(); m = local_dashboard_metrics(); sections = get_local_sections()
    st.success(f"Base temporal · {len(p.get('files', []))} archivo(s) acumulados · cartografía Sinaloa instalada")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Personas en red", f"{m['personas']:,}")
    c2.metric("Promovidos", f"{m['promovidos']:,}")
    c3.metric("Coordinadores", f"{m['coordinadores']:,}")
    c4.metric("Secciones con registros", f"{m['secciones_con_registros']:,}")
    c5,c6,c7,c8 = st.columns(4)
    c5.metric("Secciones cartografía", f"{m['secciones_catalogo']:,}")
    c6.metric("Secciones sin registros", f"{m['secciones_sin_registros']:,}")
    c7.metric("Casillas catalogadas", f"{m['casillas_catalogadas']:,}")
    c8.metric("Promovidos sin casilla", f"{m['promovidos_sin_casilla']:,}")

    if m["secciones_catalogo"]:
        pct = 100 * m["secciones_con_registros"] / m["secciones_catalogo"]
        st.progress(min(max(pct/100, 0), 1), text=f"Cobertura de secciones con registros: {pct:.1f}%")

    booth_meta = get_local_booth_catalog_meta()
    if booth_meta:
        st.info(f"🗳️ Casillas activas para pruebas: {booth_meta.get('proceso','Catálogo')} · {booth_meta.get('estatus','')} · {booth_meta.get('registros', m['casillas_catalogadas']):,} registros")
    else:
        st.warning("Casillas: todavía no hay catálogo activo. Puedes precargar el histórico IEES 2024 desde Catálogos.")

    st.subheader("Accesos operativos")
    a,b,c,d = st.columns(4)
    a.page_link("pages/05_Mapa.py",label="🗺️ Mapa poligonal",use_container_width=True)
    b.page_link("pages/10_Casillas_y_Responsables.py",label="🗳️ Casillas",use_container_width=True)
    c.page_link("pages/04_Secciones.py",label="🧭 Secciones",use_container_width=True)
    d.page_link("pages/06_Reportes.py",label="📊 Reportes",use_container_width=True)

    st.subheader("Cobertura por distrito local")
    if not sections.empty:
        cov = sections.groupby("distrito_local", dropna=False).agg(
            secciones=("numero","nunique"),
            secciones_con_registros=("promovidos", lambda x: int((x.fillna(0)>0).sum())),
            promovidos=("promovidos","sum"),
        ).reset_index()
        cov["cobertura_pct"] = (cov["secciones_con_registros"] / cov["secciones"] * 100).round(1)
        st.dataframe(cov, use_container_width=True, hide_index=True)
else:
    client=optional_client()
    if client is None:
        st.error("Supabase no disponible. Puedes seguir en modo temporal."); st.stop()
    m=dashboard_metrics(client)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Personas",m["personas"]); c2.metric("Secciones",m["secciones_con_registros"]); c3.metric("Para revisar",m["personas_revisar"]); c4.metric("Importaciones",m["importaciones_confirmadas"])

st.subheader("Lógica ejecutiva")
st.markdown("**Excel → persona → dependencia → sección → municipio/distritos derivados → casilla → coordinadores con promovidos → responsable formal.** Los datos derivados conservan su origen y el sistema no rellena con supuestos.")
