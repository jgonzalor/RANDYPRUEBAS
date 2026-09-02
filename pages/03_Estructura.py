from __future__ import annotations

import streamlit as st

from core.db import fetch_all
from core.local_store import get_local_payload, get_local_tree
from core.queries import tree_dataframe
from core.runtime import active_mode, optional_client
from core.ui import page_header

page_header("Estructura", "Dependencia jerárquica calculada: quién depende de quién")
mode = active_mode()
if mode == "LOCAL":
    payload = get_local_payload()
    df = get_local_tree()
    selected_name = payload.get("structure_name") or "Estructura temporal"
    st.caption(f"🟢 Base temporal · {selected_name}")
elif mode == "SUPABASE":
    client = optional_client()
    if client is None:
        st.warning("No se pudo conectar a Supabase.")
        st.stop()
    structures = fetch_all(client, "estructuras", select="id,nombre,persona_raiz_id", filters={"activo": True}, order="nombre")
    if not structures:
        st.info("Aún no existe ninguna estructura confirmada.")
        st.stop()
    labels = {x["nombre"]: x["id"] for x in structures}
    selected_name = st.selectbox("Estructura", list(labels))
    df = tree_dataframe(client, labels[selected_name])
else:
    st.info("Carga un Excel o activa la base demo para visualizar la red.")
    st.stop()

if df.empty:
    st.warning("No hay miembros navegables.")
    st.stop()

search = st.text_input("Buscar persona dentro de la estructura")
matched = df[df["nombre_completo"].fillna("").str.contains(search, case=False, regex=False)] if search else df
c1, c2, c3 = st.columns(3)
c1.metric("Miembros", df["persona_id"].nunique())
c2.metric("Profundidad máxima", int(df["nivel"].max()) if "nivel" in df and not df.empty else 0)
c3.metric("Resultados", len(matched))
show_cols = [c for c in ["nivel", "nombre_completo", "superior_directo_nombre", "roles", "secciones"] if c in matched.columns]
st.dataframe(matched[show_cols], use_container_width=True, hide_index=True, height=430)

st.subheader("Trazar dependencia")
options = sorted(df["nombre_completo"].dropna().unique().tolist())
person = st.selectbox("Persona", options)
row = df[df["nombre_completo"] == person].sort_values("nivel").iloc[0]
route_names = row.get("ruta_nombres") or []
if isinstance(route_names, str):
    route_names = [route_names]
if route_names:
    st.write(" → ".join(route_names))
else:
    chain = [person]
    parent = row.get("superior_directo_nombre")
    guard = set(chain)
    while parent and parent not in guard:
        chain.append(parent); guard.add(parent)
        parent_rows = df[df["nombre_completo"] == parent]
        parent = None if parent_rows.empty else parent_rows.iloc[0].get("superior_directo_nombre")
    st.write(" → ".join(reversed(chain)))

person_id = row["persona_id"]
direct = df[df["superior_directo_id"] == person_id]
st.caption(f"Dependientes directos: {len(direct)}")
if not direct.empty:
    st.dataframe(direct[[c for c in ["nombre_completo", "nivel", "roles", "secciones"] if c in direct.columns]], use_container_width=True, hide_index=True)
