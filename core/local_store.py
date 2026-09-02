from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from core.casillas import assign_records_to_booths, booth_summary
from core.cartography import enrich_normalized_with_cartography, master_sections_dataframe
from core.hierarchy import infer_root, resolve_parent_map, split_path

LOCAL_KEY = "icc_local_dataset"
FORCE_LOCAL_KEY = "icc_force_local_mode"


def _pid(name: str) -> str:
    return "local-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:16]


def has_local_data() -> bool:
    return bool(st.session_state.get(LOCAL_KEY))


def force_local_mode(enabled: bool = True) -> None:
    st.session_state[FORCE_LOCAL_KEY] = bool(enabled)


def is_local_forced() -> bool:
    return bool(st.session_state.get(FORCE_LOCAL_KEY))


def clear_local_data() -> None:
    st.session_state.pop(LOCAL_KEY, None)
    st.session_state.pop(FORCE_LOCAL_KEY, None)


def _worst_status(values: List[str]) -> str:
    priority = {"BLOQUEADO": 3, "REVISAR": 2, "LISTO": 1, "VALIDADO": 0}
    clean = [str(v) for v in values if v]
    return max(clean, key=lambda x: priority.get(x, 1)) if clean else "LISTO"


def _all_structure_names(normalized: pd.DataFrame) -> List[str]:
    if "estructura_origen" not in normalized.columns:
        return ["Estructura temporal"]
    return [x for x in normalized["estructura_origen"].dropna().astype(str).unique().tolist() if x]


def _first_nonempty(rows: pd.DataFrame, col: str):
    if rows.empty or col not in rows:
        return None
    vals = [x for x in rows[col].tolist() if pd.notna(x) and str(x).strip()]
    return vals[0] if vals else None


def _build_people_and_forest(normalized: pd.DataFrame):
    promoted_names = set(normalized.get("promovido_normalizado", pd.Series(dtype=str)).dropna().astype(str))
    all_names = set(promoted_names)
    coord_names = set()
    tree_rows: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    roots: Dict[str, Optional[str]] = {}

    for structure in _all_structure_names(normalized):
        if "estructura_origen" in normalized.columns:
            group = normalized[normalized["estructura_origen"].fillna("Estructura temporal") == structure]
        else:
            group = normalized
        records = group.to_dict("records")
        parent_map, structure_conflicts = resolve_parent_map(records)
        root = infer_root(records)
        roots[structure] = root
        for c in structure_conflicts:
            row = dict(c)
            row["estructura"] = structure
            conflicts.append(row)
        for rec in records:
            path = split_path(rec.get("ruta_jerarquica"))
            all_names.update(path)
            coord_names.update(path)
        coord_names.update(p for p in parent_map.values() if p)
        coord_names.update(k for k in parent_map if any(v == k for v in parent_map.values()))

        def chain_for(name: str):
            chain = [name]
            seen = {name}
            current = name
            while True:
                parent = parent_map.get(current)
                if not parent or parent in seen:
                    break
                chain.append(parent)
                seen.add(parent)
                current = parent
            return list(reversed(chain))

        for name in sorted(parent_map):
            route = chain_for(name)
            roles = []
            if name in promoted_names:
                roles.append("PROMOVIDO")
            if name in coord_names or name == root:
                roles.append("COORDINADOR")
            if not roles:
                roles.append("INTEGRANTE")
            tree_rows.append({
                "estructura_id": hashlib.sha1(structure.encode("utf-8")).hexdigest()[:12],
                "estructura_nombre": structure,
                "persona_id": _pid(name),
                "nombre_completo": name,
                "superior_directo_id": _pid(parent_map.get(name)) if parent_map.get(name) else None,
                "superior_directo_nombre": parent_map.get(name),
                "nivel": max(0, len(route) - 1),
                "roles": ", ".join(roles),
                "ruta_nombres": route,
            })

    for rec in normalized.to_dict("records"):
        all_names.update(split_path(rec.get("ruta_jerarquica")))
        if rec.get("promovido_normalizado"):
            all_names.add(rec["promovido_normalizado"])

    people_rows: List[Dict[str, Any]] = []
    for name in sorted(all_names):
        rows = normalized[normalized["promovido_normalizado"] == name] if "promovido_normalizado" in normalized else pd.DataFrame()
        tree_person = [r for r in tree_rows if r["nombre_completo"] == name]
        roles = []
        if name in promoted_names:
            roles.append("PROMOVIDO")
        if name in coord_names or any("COORDINADOR" in r["roles"] for r in tree_person):
            roles.append("COORDINADOR")
        if not roles:
            roles.append("INTEGRANTE")
        primary = tree_person[0] if tree_person else {}
        structures = sorted({r["estructura_nombre"] for r in tree_person})
        people_rows.append({
            "persona_id": _pid(name),
            "nombre_completo": name,
            "telefono": _first_nonempty(rows, "telefono"),
            "roles": ", ".join(roles),
            "superior_directo_nombre": primary.get("superior_directo_nombre"),
            "superior_directo_id": primary.get("superior_directo_id"),
            "municipio": _first_nonempty(rows, "municipio"),
            "municipio_origen": _first_nonempty(rows, "municipio_origen"),
            "seccion": _first_nonempty(rows, "seccion"),
            "distrito_local": _first_nonempty(rows, "distrito_local"),
            "distrito_federal": _first_nonempty(rows, "distrito_federal"),
            "tipo_seccion": _first_nonempty(rows, "tipo_seccion"),
            "estado_validacion": _worst_status(rows.get("estado_validacion", pd.Series(dtype=str)).tolist()) if not rows.empty else "LISTO",
            "calle": _first_nonempty(rows, "calle"),
            "colonia": _first_nonempty(rows, "colonia"),
            "localidad": _first_nonempty(rows, "localidad"),
            "estructuras": ", ".join(structures),
            "archivo_origen": _first_nonempty(rows, "archivo_origen"),
        })
    people = pd.DataFrame(people_rows)
    tree = pd.DataFrame(tree_rows)
    if not tree.empty:
        tree = tree.sort_values(["estructura_nombre", "nivel", "nombre_completo"])
    return people, tree, roots, conflicts


def _build_coordinator_section(normalized: pd.DataFrame) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame()
    work = normalized.dropna(subset=["seccion", "promovido_normalizado"]).copy()
    if work.empty:
        return pd.DataFrame()
    work["coordinador"] = work["superior_directo"]
    rows = []
    for keys, g in work.groupby(["municipio", "seccion", "coordinador"], dropna=False):
        muni, sec, coord = keys
        if not coord:
            continue
        rows.append({
            "municipio": muni,
            "seccion": sec,
            "distrito_local": _first_nonempty(g, "distrito_local"),
            "distrito_federal": _first_nonempty(g, "distrito_federal"),
            "coordinador": coord,
            "promovidos": int(g["promovido_normalizado"].nunique()),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    totals = out.groupby(["municipio", "seccion"])["promovidos"].transform("sum")
    out["porcentaje_seccion"] = (out["promovidos"] / totals * 100).round(1)
    return out.sort_values(["municipio", "seccion", "promovidos"], ascending=[True, True, False])


def _build_sections(normalized: pd.DataFrame, coordinator_section: pd.DataFrame) -> pd.DataFrame:
    # El catálogo cartográfico es la base maestra: permite ver también las secciones sin registros.
    master = master_sections_dataframe()
    if master.empty:
        master = pd.DataFrame(columns=["numero", "municipio", "distrito_local", "distrito_federal", "tipo_seccion", "centroide_lat", "centroide_lon"])
    sections = master.copy()
    sections["seccion_id"] = sections["numero"].map(lambda x: f"local-sec-{int(x)}" if pd.notna(x) else None)
    sections["municipio_conflicto"] = False
    sections["estado_catalogo"] = "CARTOGRAFIA_PRECARGADA"
    sections["personas_registradas"] = 0
    sections["promovidos"] = 0
    sections["coordinadores"] = 0
    sections["coordinador_mayor_estructura"] = None
    sections["promovidos_coordinador_top"] = 0
    sections["responsable_formal"] = None
    sections["casillas_catalogadas"] = 0
    sections["casillas_con_promovidos"] = 0
    sections["promovidos_sin_casilla"] = 0

    known = set(pd.to_numeric(sections.get("numero", pd.Series(dtype=float)), errors="coerce").dropna().astype(int).tolist())
    unknown_rows: List[Dict[str, Any]] = []

    if not normalized.empty and "seccion" in normalized.columns:
        work = normalized.dropna(subset=["seccion"]).copy()
        for section, g in work.groupby("seccion", dropna=False):
            try:
                sec_num = int(float(section))
            except Exception:
                sec_num = section
            promoted = set(x for x in g.get("promovido_normalizado", pd.Series(dtype=str)).dropna().astype(str) if x)
            coords = coordinator_section[coordinator_section["seccion"].astype(str) == str(section)] if not coordinator_section.empty else pd.DataFrame()
            top = coords.iloc[0] if not coords.empty else None
            values = {
                "personas_registradas": len(promoted),
                "promovidos": len(promoted),
                "coordinadores": int(coords["coordinador"].nunique()) if not coords.empty else 0,
                "coordinador_mayor_estructura": None if top is None else top["coordinador"],
                "promovidos_coordinador_top": 0 if top is None else int(top["promovidos"]),
                "promovidos_sin_casilla": len(promoted),
            }
            if isinstance(sec_num, int) and sec_num in known:
                mask = pd.to_numeric(sections["numero"], errors="coerce") == sec_num
                for k, v in values.items():
                    sections.loc[mask, k] = v
            else:
                municipality = _first_nonempty(g, "municipio")
                unknown_rows.append({
                    "numero": sec_num,
                    "municipio": municipality,
                    "distrito_local": _first_nonempty(g, "distrito_local"),
                    "distrito_federal": _first_nonempty(g, "distrito_federal"),
                    "tipo_seccion": _first_nonempty(g, "tipo_seccion"),
                    "centroide_lat": _first_nonempty(g, "centroide_lat"),
                    "centroide_lon": _first_nonempty(g, "centroide_lon"),
                    "seccion_id": f"local-sec-{sec_num}",
                    "municipio_conflicto": False,
                    "estado_catalogo": "NO_LOCALIZADA",
                    "responsable_formal": None,
                    "casillas_catalogadas": 0,
                    "casillas_con_promovidos": 0,
                    **values,
                })
    if unknown_rows:
        sections = pd.concat([sections, pd.DataFrame(unknown_rows)], ignore_index=True, sort=False)
    return sections.sort_values(["municipio", "numero"], na_position="last").reset_index(drop=True)




def _cross_file_incidents(normalized: pd.DataFrame) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame()
    rows = []
    if "archivo_origen" in normalized.columns and "promovido_normalizado" in normalized.columns:
        for name, g in normalized.dropna(subset=["promovido_normalizado"]).groupby("promovido_normalizado"):
            files = sorted(set(g.get("archivo_origen", pd.Series(dtype=str)).dropna().astype(str)))
            parents = sorted(set(g.get("superior_directo", pd.Series(dtype=str)).dropna().astype(str)))
            sections = sorted(set(g.get("seccion", pd.Series(dtype=str)).dropna().astype(str)))
            if len(files) > 1:
                rows.append({"fila_excel": None, "severidad": "INFO", "tipo": "PERSONA_REPETIDA_ENTRE_ARCHIVOS", "campo": "persona", "valor": name, "mensaje": f"La persona aparece en {len(files)} archivos: {', '.join(files)}.", "origen_incidencia": "CONSOLIDACION"})
            if len(parents) > 1:
                rows.append({"fila_excel": None, "severidad": "ADVERTENCIA", "tipo": "CONFLICTO_SUPERIOR_ENTRE_ARCHIVOS", "campo": "superior_directo", "valor": name, "mensaje": f"La persona aparece con superiores distintos: {', '.join(parents)}.", "origen_incidencia": "CONSOLIDACION"})
            if len(sections) > 1:
                rows.append({"fila_excel": None, "severidad": "ADVERTENCIA", "tipo": "MULTIPLES_SECCIONES_PERSONA", "campo": "seccion", "valor": name, "mensaje": f"La persona aparece asociada a varias secciones: {', '.join(sections)}. Revisar si corresponde a residencia/operación o a duplicidad.", "origen_incidencia": "CONSOLIDACION"})
    if "telefono" in normalized.columns:
        for phone, g in normalized.dropna(subset=["telefono"]).groupby("telefono"):
            names = sorted(set(g.get("promovido_normalizado", pd.Series(dtype=str)).dropna().astype(str)))
            if len(names) > 1:
                rows.append({"fila_excel": None, "severidad": "ADVERTENCIA", "tipo": "TELEFONO_COMPARTIDO_NOMBRES", "campo": "telefono", "valor": phone, "mensaje": f"El teléfono está asociado a nombres distintos: {', '.join(names)}.", "origen_incidencia": "CONSOLIDACION"})
    return pd.DataFrame(rows)

def _rebuild_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    raw_normalized = p.get("normalized", pd.DataFrame()).copy()
    normalized, territory_incidents = enrich_normalized_with_cartography(raw_normalized)
    p["normalized"] = normalized

    base_inc = p.get("incidents_base")
    if not isinstance(base_inc, pd.DataFrame):
        base_inc = p.get("incidents", pd.DataFrame()).copy()
    if not territory_incidents.empty:
        territory_incidents["origen_incidencia"] = "CARTOGRAFIA"
    cross_incidents = _cross_file_incidents(normalized)
    chunks = [x for x in (base_inc, territory_incidents, cross_incidents) if isinstance(x, pd.DataFrame) and not x.empty]
    incidents = pd.concat(chunks, ignore_index=True, sort=False) if chunks else pd.DataFrame()
    p["incidents"] = incidents

    people, tree, roots, conflicts = _build_people_and_forest(normalized)
    coord_section = _build_coordinator_section(normalized)
    sections = _build_sections(normalized, coord_section)
    booths = p.get("booths", pd.DataFrame()).copy()
    responsibilities = p.get("responsibilities", pd.DataFrame()).copy()
    assignments = assign_records_to_booths(normalized, booths) if not booths.empty else pd.DataFrame()
    booth_s = booth_summary(assignments, responsibilities)

    if not sections.empty and not booths.empty:
        booth_counts = booths.groupby("seccion")["casilla_id"].nunique().to_dict()
        assigned_counts = booth_s.groupby("seccion")["casilla_id"].nunique().to_dict() if not booth_s.empty else {}
        pending_counts = assignments[assignments["casilla_id"].isna()].groupby("seccion")["promovido"].nunique().to_dict() if not assignments.empty else {}
        sections["casillas_catalogadas"] = sections["numero"].map(booth_counts).fillna(0).astype(int)
        sections["casillas_con_promovidos"] = sections["numero"].map(assigned_counts).fillna(0).astype(int)
        sections["promovidos_sin_casilla"] = sections["numero"].map(pending_counts).fillna(0).astype(int)

    if not responsibilities.empty and not sections.empty:
        sec_resp = responsibilities[(responsibilities["tipo_territorio"] == "SECCION") & (responsibilities["activo"] == True)]
        by = {str(r["territorio_id"]): r["responsable_nombre"] for _, r in sec_resp.iterrows()}
        sections["responsable_formal"] = sections["seccion_id"].astype(str).map(by)

    p.update({
        "people": people,
        "tree": tree,
        "roots": roots,
        "hierarchy_conflicts": conflicts,
        "coordinator_section": coord_section,
        "sections": sections,
        "booth_assignments": assignments,
        "booth_summary": booth_s,
    })
    return p


def activate_local_dataset(
    normalized: pd.DataFrame,
    incidents: Optional[pd.DataFrame],
    structure_name: str,
    filename: str,
    source_kind: str = "EXCEL_TEMPORAL",
    append: bool = False,
) -> Dict[str, Any]:
    new = normalized.copy()
    new["estructura_origen"] = structure_name
    new["archivo_origen"] = filename
    inc = incidents.copy() if isinstance(incidents, pd.DataFrame) else pd.DataFrame()
    if not inc.empty:
        inc["estructura_origen"] = structure_name
        inc["archivo_origen"] = filename
        inc["origen_incidencia"] = "IMPORTACION"

    if append and has_local_data():
        p = get_local_payload()
        combined = pd.concat([p.get("normalized", pd.DataFrame()), new], ignore_index=True, sort=False)
        old_base = p.get("incidents_base", p.get("incidents", pd.DataFrame()))
        combined_inc = pd.concat([old_base, inc], ignore_index=True, sort=False)
        files = list(p.get("files", [])) + [{
            "filename": filename,
            "structure_name": structure_name,
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": len(new),
        }]
        p.update({
            "normalized": combined,
            "incidents_base": combined_inc,
            "files": files,
            "filename": f"{len(files)} archivos acumulados",
            "structure_name": "Base consolidada",
            "source_kind": "EXCEL_MULTIPLE",
        })
    else:
        p = {
            "source_kind": source_kind,
            "filename": filename,
            "structure_name": structure_name,
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "normalized": new,
            "incidents_base": inc,
            "incidents": inc,
            "files": [{
                "filename": filename,
                "structure_name": structure_name,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "rows": len(new),
            }],
            "booths": pd.DataFrame(),
            "booth_catalog_meta": {},
            "responsibilities": pd.DataFrame(),
        }
    p = _rebuild_payload(p)
    st.session_state[LOCAL_KEY] = p
    force_local_mode(True)
    return p


def set_local_booths(booths: pd.DataFrame, meta: Optional[Dict[str, Any]] = None) -> None:
    p = get_local_payload()
    p["booths"] = booths.copy()
    if meta is not None:
        p["booth_catalog_meta"] = dict(meta)
    st.session_state[LOCAL_KEY] = _rebuild_payload(p)


def add_local_responsibility(responsable_nombre: str, tipo_territorio: str, territorio_id: str, territorio_label: str) -> None:
    p = get_local_payload()
    df = p.get("responsibilities", pd.DataFrame()).copy()
    if not df.empty:
        df.loc[(df["tipo_territorio"] == tipo_territorio) & (df["territorio_id"] == territorio_id), "activo"] = False
    row = {
        "responsable_nombre": responsable_nombre,
        "tipo_territorio": tipo_territorio,
        "territorio_id": territorio_id,
        "territorio_label": territorio_label,
        "activo": True,
        "asignado_en": datetime.now(timezone.utc).isoformat(),
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    p["responsibilities"] = df
    st.session_state[LOCAL_KEY] = _rebuild_payload(p)


def get_local_payload() -> Dict[str, Any]:
    return st.session_state.get(LOCAL_KEY) or {}


def get_local_people() -> pd.DataFrame:
    return get_local_payload().get("people", pd.DataFrame()).copy()


def get_local_tree() -> pd.DataFrame:
    return get_local_payload().get("tree", pd.DataFrame()).copy()


def get_local_sections() -> pd.DataFrame:
    return get_local_payload().get("sections", pd.DataFrame()).copy()


def get_local_incidents() -> pd.DataFrame:
    return get_local_payload().get("incidents", pd.DataFrame()).copy()


def get_local_booths() -> pd.DataFrame:
    return get_local_payload().get("booths", pd.DataFrame()).copy()


def get_local_booth_catalog_meta() -> Dict[str, Any]:
    return dict(get_local_payload().get("booth_catalog_meta") or {})


def get_local_booth_assignments() -> pd.DataFrame:
    return get_local_payload().get("booth_assignments", pd.DataFrame()).copy()


def get_local_booth_summary() -> pd.DataFrame:
    return get_local_payload().get("booth_summary", pd.DataFrame()).copy()


def get_local_coordinator_section() -> pd.DataFrame:
    return get_local_payload().get("coordinator_section", pd.DataFrame()).copy()


def get_local_responsibilities() -> pd.DataFrame:
    return get_local_payload().get("responsibilities", pd.DataFrame()).copy()


def local_dashboard_metrics() -> Dict[str, int]:
    p = get_local_payload()
    people = get_local_people()
    sections = get_local_sections()
    incidents = get_local_incidents()
    normalized = p.get("normalized", pd.DataFrame())
    booths = get_local_booths()
    assignments = get_local_booth_assignments()
    presence = sections[sections.get("promovidos", pd.Series(index=sections.index, dtype=int)).fillna(0) > 0] if not sections.empty else pd.DataFrame()
    return {
        "personas": len(people),
        "promovidos": int(people["roles"].fillna("").str.contains("PROMOVIDO").sum()) if not people.empty else 0,
        "coordinadores": int(people["roles"].fillna("").str.contains("COORDINADOR").sum()) if not people.empty else 0,
        "personas_revisar": int((normalized.get("estado_validacion", pd.Series(dtype=str)) == "REVISAR").sum()) if not normalized.empty else 0,
        "secciones_con_registros": len(presence),
        "secciones_catalogo": int((sections.get("estado_catalogo", pd.Series(dtype=str)) == "CARTOGRAFIA_PRECARGADA").sum()) if not sections.empty else 0,
        "secciones_sin_registros": int((sections.get("promovidos", pd.Series(dtype=int)).fillna(0) == 0).sum()) if not sections.empty else 0,
        "importaciones": len(p.get("files", [])),
        "importaciones_confirmadas": 0,
        "incidencias": len(incidents),
        "casillas_catalogadas": int(len(booths)),
        "casillas_con_promovidos": int(assignments["casilla_id"].dropna().nunique()) if not assignments.empty else 0,
        "promovidos_sin_casilla": int(assignments[assignments["casilla_id"].isna()]["promovido"].nunique()) if not assignments.empty else int(normalized.get("promovido_normalizado", pd.Series(dtype=str)).nunique()),
    }


def build_demo_dataset() -> Dict[str, Any]:
    # Usa secciones reales del catálogo precargado para que el mapa demo también funcione.
    demo_secs = [316, 317, 318, 319, 320, 321, 322, 323]
    rows = []
    row_num = 2
    for g1 in range(1, 5):
        coord1 = f"COORDINADOR DEMO {g1:02d}"
        for g2 in range(1, 4):
            coord2 = f"ENLACE DEMO {g1:02d}-{g2:02d}"
            for pp in range(1, 5):
                idx = (g1 - 1) * 12 + (g2 - 1) * 4 + pp
                section = demo_secs[(idx - 1) % len(demo_secs)]
                rows.append({
                    "fila_excel": row_num,
                    "promovido_original": f"PERSONA DEMO {idx:03d}",
                    "promovido_normalizado": f"PERSONA DEMO {idx:03d}",
                    "telefono": f"668{idx:07d}"[-10:],
                    "seccion": section,
                    "municipio": "AHOME",
                    "superior_directo": coord2,
                    "ruta_jerarquica": f"COORDINACION DEMO > {coord1} > {coord2}",
                    "nivel_desde_raiz": 3,
                    "apellido_paterno": chr(65 + (idx % 20)) + "PELLIDO",
                    "apellido_materno": None,
                    "calle": None,
                    "numero_exterior": None,
                    "numero_interior": None,
                    "colonia": None,
                    "localidad": None,
                    "codigo_postal": None,
                    "referencias": None,
                    "casilla_original": None,
                    "estado_validacion": "LISTO",
                    "posible_duplicado_nombre": False,
                    "posible_duplicado_telefono": False,
                })
                row_num += 1
    p = activate_local_dataset(pd.DataFrame(rows), pd.DataFrame(), "Estructura demostrativa", "DEMO_INTEGRADO", source_kind="DEMO_SINTETICO")
    # Catálogo demo de casillas: únicamente para explorar asignación por rangos.
    booths = []
    for sec in demo_secs:
        booths.append({"casilla_id": f"local-cas-{sec}-B", "seccion": sec, "municipio": "AHOME", "tipo_casilla": "B", "numero_casilla": None, "clave_casilla": f"{sec} B", "apellido_desde": "A", "apellido_hasta": "M", "localidad": None, "domicilio": None, "distrito_local": None, "distrito_federal": None, "lista_nominal": None, "fuente_catalogo": "DEMO", "proceso_electoral": "DEMO"})
        booths.append({"casilla_id": f"local-cas-{sec}-C1", "seccion": sec, "municipio": "AHOME", "tipo_casilla": "C1", "numero_casilla": 1, "clave_casilla": f"{sec} C1", "apellido_desde": "N", "apellido_hasta": "Z", "localidad": None, "domicilio": None, "distrito_local": None, "distrito_federal": None, "lista_nominal": None, "fuente_catalogo": "DEMO", "proceso_electoral": "DEMO"})
    set_local_booths(pd.DataFrame(booths), {"proceso": "DEMO", "estatus": "SINTETICO", "fuente": "Demo integrado"})
    return get_local_payload()


def local_imports_dataframe() -> pd.DataFrame:
    p = get_local_payload()
    files = p.get("files", [])
    return pd.DataFrame([{
        "created_at": x.get("loaded_at"),
        "filename": x.get("filename"),
        "sheet_name": "Temporal",
        "structure_name": x.get("structure_name"),
        "total_rows": x.get("rows"),
        "status": "TEMPORAL",
        "confirmed_at": None,
        "id": f"LOCAL-{i + 1}",
    } for i, x in enumerate(files)])


def local_add_person(name: str, phone: Optional[str], parent_name: Optional[str], role: str, section: Optional[Any], municipality: Optional[str]) -> None:
    p = get_local_payload()
    name = (name or "").strip().upper()
    if not p:
        raise RuntimeError("No hay base temporal activa.")
    if not name:
        raise ValueError("El nombre es obligatorio.")
    normalized = p.get("normalized", pd.DataFrame()).copy()
    if name in set(normalized.get("promovido_normalizado", pd.Series(dtype=str)).dropna().astype(str)):
        raise ValueError("Ya existe una persona promovida con ese nombre.")
    row = {
        "fila_excel": None,
        "promovido_original": name,
        "promovido_normalizado": name,
        "telefono": phone or None,
        "seccion": section or None,
        "municipio": municipality or None,
        "superior_directo": parent_name or None,
        "ruta_jerarquica": parent_name or None,
        "nivel_desde_raiz": 1 if parent_name else 0,
        "apellido_paterno": None,
        "apellido_materno": None,
        "casilla_original": None,
        "calle": None,
        "numero_exterior": None,
        "numero_interior": None,
        "colonia": None,
        "localidad": None,
        "codigo_postal": None,
        "referencias": None,
        "estado_validacion": "LISTO",
        "posible_duplicado_nombre": False,
        "posible_duplicado_telefono": False,
        "estructura_origen": "Captura manual",
        "archivo_origen": "CAPTURA_MANUAL",
    }
    p["normalized"] = pd.concat([normalized, pd.DataFrame([row])], ignore_index=True, sort=False)
    st.session_state[LOCAL_KEY] = _rebuild_payload(p)
