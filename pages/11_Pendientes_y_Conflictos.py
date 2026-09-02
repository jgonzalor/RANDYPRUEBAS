from __future__ import annotations

import pandas as pd
import streamlit as st

from core.local_store import (
    get_local_booth_assignments, get_local_incidents, get_local_people,
    get_local_sections, get_local_tree,
)
from core.runtime import active_mode
from core.ui import page_header

page_header("Pendientes y conflictos", "Centro de control de calidad: datos faltantes, conflictos territoriales y asignaciones pendientes")
if active_mode() != "LOCAL":
    st.info("Esta vista V2 se prueba primero en modo temporal.")
    st.stop()

people=get_local_people(); sections=get_local_sections(); incidents=get_local_incidents(); assignments=get_local_booth_assignments(); tree=get_local_tree()

no_phone=people[people.get("telefono",pd.Series(index=people.index,dtype=object)).isna()] if not people.empty else pd.DataFrame()
no_section=people[people.get("seccion",pd.Series(index=people.index,dtype=object)).isna()] if not people.empty else pd.DataFrame()
no_parent=people[(people.get("superior_directo_nombre",pd.Series(index=people.index,dtype=object)).isna()) & people.get("roles",pd.Series(index=people.index,dtype=str)).fillna("").str.contains("PROMOVIDO")] if not people.empty else pd.DataFrame()
with_presence=sections[sections.get("promovidos",pd.Series(index=sections.index,dtype=int)).fillna(0)>0] if not sections.empty else pd.DataFrame()
no_resp=with_presence[with_presence.get("responsable_formal",pd.Series(index=with_presence.index,dtype=object)).isna()] if not with_presence.empty else pd.DataFrame()
no_coord=with_presence[with_presence.get("coordinadores",pd.Series(index=with_presence.index,dtype=int)).fillna(0)==0] if not with_presence.empty else pd.DataFrame()
pending_booth=assignments[assignments.get("casilla_id",pd.Series(index=assignments.index,dtype=object)).isna()] if not assignments.empty else pd.DataFrame()
territorial=incidents[incidents.get("origen_incidencia",pd.Series(index=incidents.index,dtype=str)).fillna("")=="CARTOGRAFIA"] if not incidents.empty else pd.DataFrame()

c1,c2,c3,c4=st.columns(4)
c1.metric("Incidencias",len(incidents)); c2.metric("Conflictos territoriales",len(territorial)); c3.metric("Promovidos sin casilla",pending_booth["promovido"].nunique() if not pending_booth.empty else 0); c4.metric("Secciones sin responsable",len(no_resp))
c5,c6,c7,c8=st.columns(4)
c5.metric("Personas sin teléfono",len(no_phone)); c6.metric("Personas sin sección",len(no_section)); c7.metric("Promovidos sin superior",len(no_parent)); c8.metric("Secciones sin coordinador",len(no_coord))

tabs=st.tabs(["Incidencias","Casillas pendientes","Responsables","Personas incompletas"])
with tabs[0]:
    if incidents.empty: st.success("No hay incidencias registradas.")
    else:
        sev=st.multiselect("Severidad",sorted(incidents.get("severidad",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()),default=sorted(incidents.get("severidad",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()))
        f=incidents[incidents["severidad"].isin(sev)] if sev and "severidad" in incidents else incidents
        st.dataframe(f,use_container_width=True,hide_index=True,height=520)
with tabs[1]:
    if pending_booth.empty: st.success("No hay promovidos pendientes de casilla.")
    else:
        st.dataframe(pending_booth[[c for c in ["promovido","coordinador_directo","seccion","municipio","estado_asignacion","criterio_asignacion","archivo_origen"] if c in pending_booth]],use_container_width=True,hide_index=True,height=520)
with tabs[2]:
    st.subheader("Secciones con registros sin responsable formal")
    if no_resp.empty: st.success("Todas las secciones con registros tienen responsable formal.")
    else: st.dataframe(no_resp[[c for c in ["numero","municipio","distrito_local","distrito_federal","promovidos","coordinador_mayor_estructura"] if c in no_resp]],use_container_width=True,hide_index=True,height=420)
with tabs[3]:
    choice=st.radio("Mostrar",["Sin teléfono","Sin sección","Promovidos sin superior"],horizontal=True)
    data={"Sin teléfono":no_phone,"Sin sección":no_section,"Promovidos sin superior":no_parent}[choice]
    if data.empty: st.success("Sin pendientes en esta categoría.")
    else: st.dataframe(data,use_container_width=True,hide_index=True,height=500)
