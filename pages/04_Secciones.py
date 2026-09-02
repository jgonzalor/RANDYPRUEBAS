from __future__ import annotations
import pandas as pd
import streamlit as st
from core.local_store import get_local_sections
from core.queries import sections_dataframe
from core.runtime import active_mode, optional_client
from core.ui import page_header

page_header("Secciones", "Catálogo territorial completo y cobertura agregada por sección electoral")
mode=active_mode()
if mode=="LOCAL": df=get_local_sections(); st.caption("🟢 Cartografía Sinaloa precargada + base temporal")
elif mode=="SUPABASE":
    client=optional_client();
    if client is None: st.stop()
    df=sections_dataframe(client)
else: st.info("Carga un Excel o activa demo."); st.stop()
if df.empty: st.info("Sin secciones."); st.stop()

f=df.copy()
munis=["TODOS"]+sorted(f["municipio"].dropna().astype(str).unique().tolist()); muni=st.selectbox("Municipio",munis)
locales=["TODOS"]+sorted(pd.to_numeric(f.get("distrito_local"),errors="coerce").dropna().astype(int).unique().tolist()); dl=st.selectbox("Distrito local",locales)
federales=["TODOS"]+sorted(pd.to_numeric(f.get("distrito_federal"),errors="coerce").dropna().astype(int).unique().tolist()); dfed=st.selectbox("Distrito federal",federales)
pres=st.selectbox("Cobertura",["TODAS","CON REGISTROS","SIN REGISTROS"])
q=st.text_input("Buscar sección")
if muni!="TODOS": f=f[f["municipio"]==muni]
if dl!="TODOS": f=f[pd.to_numeric(f["distrito_local"],errors="coerce")==int(dl)]
if dfed!="TODOS": f=f[pd.to_numeric(f["distrito_federal"],errors="coerce")==int(dfed)]
if pres=="CON REGISTROS": f=f[f["promovidos"].fillna(0)>0]
elif pres=="SIN REGISTROS": f=f[f["promovidos"].fillna(0)==0]
if q: f=f[f["numero"].astype(str).str.contains(q,regex=False)]

c1,c2,c3,c4=st.columns(4)
c1.metric("Secciones",f"{len(f):,}"); c2.metric("Con registros",f"{int((f['promovidos'].fillna(0)>0).sum()):,}"); c3.metric("Promovidos",f"{int(f['promovidos'].fillna(0).sum()):,}"); c4.metric("Casillas catalogadas",f"{int(f['casillas_catalogadas'].fillna(0).sum()):,}")
cols=[c for c in ["numero","municipio","distrito_local","distrito_federal","tipo_seccion","promovidos","coordinadores","coordinador_mayor_estructura","promovidos_coordinador_top","responsable_formal","casillas_catalogadas","casillas_con_promovidos","promovidos_sin_casilla","estado_catalogo"] if c in f]
display=f[cols].copy()
for c in ["coordinador_mayor_estructura","responsable_formal","tipo_seccion"]:
    if c in display: display[c]=display[c].fillna("No disponible")
st.dataframe(display,use_container_width=True,hide_index=True,height=590)
