from __future__ import annotations
import pandas as pd
import streamlit as st
from core.local_store import get_local_booth_summary, get_local_coordinator_section, get_local_people, get_local_sections
from core.queries import people_dataframe, sections_dataframe
from core.runtime import active_mode, optional_client
from core.ui import page_header

page_header("Reportes V2", "Concentrados ejecutivos enriquecidos con información territorial derivada de la sección")
mode=active_mode()
if mode=="LOCAL": people=get_local_people(); sections=get_local_sections(); coord=get_local_coordinator_section(); booths=get_local_booth_summary()
elif mode=="SUPABASE":
    client=optional_client();
    if client is None: st.stop()
    people=people_dataframe(client); sections=sections_dataframe(client); coord=pd.DataFrame(); booths=pd.DataFrame()
else: st.info("Carga datos primero."); st.stop()
if people.empty: st.stop()

def display_ready(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    for c in out.columns:
        if out[c].dtype==object: out[c]=out[c].fillna("No disponible")
    return out

t1,t2,t3,t4=st.tabs(["Territorio","Distritos","Coordinadores","Casillas"])
with t1:
    presence=sections[sections["promovidos"].fillna(0)>0].copy() if not sections.empty else pd.DataFrame()
    if not presence.empty:
        cols=[c for c in ["numero","municipio","distrito_local","distrito_federal","tipo_seccion","promovidos","coordinadores","coordinador_mayor_estructura","responsable_formal","casillas_catalogadas","promovidos_sin_casilla"] if c in presence]
        st.dataframe(display_ready(presence[cols]),use_container_width=True,hide_index=True,height=520)
        st.download_button("Descargar secciones con presencia CSV",display_ready(presence[cols]).to_csv(index=False).encode("utf-8-sig"),"reporte_secciones.csv","text/csv")
with t2:
    if not sections.empty:
        dl=sections.groupby("distrito_local",dropna=False).agg(secciones=("numero","nunique"),secciones_con_registros=("promovidos",lambda x:int((x.fillna(0)>0).sum())),promovidos=("promovidos","sum"),coordinadores=("coordinadores","sum")).reset_index()
        dl["cobertura_pct"]=(dl["secciones_con_registros"]/dl["secciones"]*100).round(1)
        st.subheader("Distrito local"); st.dataframe(dl,use_container_width=True,hide_index=True)
        dfed=sections.groupby("distrito_federal",dropna=False).agg(secciones=("numero","nunique"),secciones_con_registros=("promovidos",lambda x:int((x.fillna(0)>0).sum())),promovidos=("promovidos","sum")).reset_index()
        dfed["cobertura_pct"]=(dfed["secciones_con_registros"]/dfed["secciones"]*100).round(1)
        st.subheader("Distrito federal"); st.dataframe(dfed,use_container_width=True,hide_index=True)
with t3:
    if coord.empty: st.info("Sin ranking disponible.")
    else:
        rank=coord.groupby("coordinador").agg(promovidos=("promovidos","sum"),secciones=("seccion","nunique")).reset_index().sort_values(["promovidos","secciones"],ascending=False)
        st.caption("Tamaño de estructura registrada; no se interpreta automáticamente como efectividad.")
        st.dataframe(rank,use_container_width=True,hide_index=True,height=500); st.bar_chart(rank.head(20).set_index("coordinador")["promovidos"])
with t4:
    if booths.empty: st.info("Activa un catálogo de casillas para habilitar este concentrado.")
    else: st.dataframe(display_ready(booths),use_container_width=True,hide_index=True,height=540)
