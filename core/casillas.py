from __future__ import annotations

import json
import re
import unicodedata
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


def _clean(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _key(value: Any) -> Optional[str]:
    text = _clean(value)
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text.upper()).strip()
    return text or None


def normalize_booth_type(value: Any) -> Optional[str]:
    v = _key(value)
    if not v:
        return None
    if v == "B" or v.startswith("BASICA") or v.startswith("BASICO"):
        return "B"
    if v.startswith("C") or "CONTIG" in v:
        m = re.search(r"(\d+)", v)
        return f"C{m.group(1)}" if m else "C1"
    if v.startswith("E") or "EXTRA" in v:
        m = re.search(r"(\d+)", v)
        return f"E{m.group(1)}" if m else "E1"
    if v.startswith("S") or "ESPEC" in v:
        m = re.search(r"(\d+)", v)
        return f"S{m.group(1)}" if m else "S1"
    return v


BOOTH_ALIASES = {
    "seccion": ["SECCION", "SECCIÓN"],
    "municipio": ["MUNICIPIO"],
    "tipo": ["TIPO CASILLA", "TIPO", "CASILLA TIPO", "TIPO_CASILLA"],
    "numero": ["NUMERO CASILLA", "NÚMERO CASILLA", "NUM CASILLA", "NUMERO", "NÚMERO"],
    "clave": ["CLAVE CASILLA", "CASILLA", "CLAVE"],
    "apellido_desde": ["APELLIDO DESDE", "INICIAL DESDE", "RANGO DESDE", "DESDE"],
    "apellido_hasta": ["APELLIDO HASTA", "INICIAL HASTA", "RANGO HASTA", "HASTA"],
    "localidad": ["LOCALIDAD"],
    "domicilio": ["DOMICILIO", "DIRECCION", "DIRECCIÓN", "UBICACION", "UBICACIÓN"],
    "distrito_local": ["DISTRITO LOCAL", "DISTRITO_LOCAL", "DTTO LOCAL", "DTO LOCAL"],
    "distrito_federal": ["DISTRITO FEDERAL", "DISTRITO_FEDERAL", "DTTO FEDERAL", "DTO FEDERAL"],
    "lista_nominal": ["LISTA NOMINAL", "LISTA_NOMINAL", "LN"],
    "padron_electoral": ["PADRON ELECTORAL", "PADRÓN ELECTORAL", "PADRON", "PE"],
}


def detect_booth_columns(columns: Iterable[Any]) -> Dict[str, Optional[str]]:
    by = {_key(c): str(c) for c in columns}
    out: Dict[str, Optional[str]] = {}
    for field, aliases in BOOTH_ALIASES.items():
        out[field] = next((by.get(_key(a)) for a in aliases if by.get(_key(a))), None)
    return out


def read_booth_catalog(data: bytes, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    excel = pd.ExcelFile(BytesIO(data))
    sheets = excel.sheet_names
    selected = sheet_name or sheets[0]
    df = pd.read_excel(BytesIO(data), sheet_name=selected, dtype=object).dropna(how="all").reset_index(drop=True)
    return df, sheets


def normalize_booth_catalog(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    mapping = detect_booth_columns(df.columns)
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        section_raw = r.get(mapping.get("seccion")) if mapping.get("seccion") else None
        try:
            section = int(float(section_raw)) if section_raw is not None and str(section_raw).strip() else None
        except Exception:
            section = None
        booth_type = normalize_booth_type(r.get(mapping.get("tipo")) if mapping.get("tipo") else None)
        num_raw = r.get(mapping.get("numero")) if mapping.get("numero") else None
        try:
            number = int(float(num_raw)) if num_raw is not None and str(num_raw).strip() else None
        except Exception:
            number = None
        explicit_key = _clean(r.get(mapping.get("clave")) if mapping.get("clave") else None)
        if not booth_type and explicit_key:
            booth_type = normalize_booth_type(explicit_key)
        if booth_type and booth_type[0] in {"C", "E", "S"} and len(booth_type) > 1 and number is None:
            try:
                number = int(booth_type[1:])
            except Exception:
                pass
        if section and booth_type:
            ex_key = _key(explicit_key) if explicit_key else None
            label = explicit_key if ex_key and str(section) in ex_key else f"{section} {booth_type}"
        else:
            label = explicit_key
        rows.append({
            "seccion": section,
            "municipio": _key(r.get(mapping.get("municipio")) if mapping.get("municipio") else None),
            "tipo_casilla": booth_type,
            "numero_casilla": number,
            "clave_casilla": label,
            "apellido_desde": _key(r.get(mapping.get("apellido_desde")) if mapping.get("apellido_desde") else None),
            "apellido_hasta": _key(r.get(mapping.get("apellido_hasta")) if mapping.get("apellido_hasta") else None),
            "localidad": _key(r.get(mapping.get("localidad")) if mapping.get("localidad") else None),
            "domicilio": _clean(r.get(mapping.get("domicilio")) if mapping.get("domicilio") else None),
            "distrito_local": _clean(r.get(mapping.get("distrito_local")) if mapping.get("distrito_local") else None),
            "distrito_federal": _clean(r.get(mapping.get("distrito_federal")) if mapping.get("distrito_federal") else None),
            "lista_nominal": _clean(r.get(mapping.get("lista_nominal")) if mapping.get("lista_nominal") else None),
            "padron_electoral": _clean(r.get(mapping.get("padron_electoral")) if mapping.get("padron_electoral") else None),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out[out["seccion"].notna() & out["tipo_casilla"].notna()].copy()
        out["casilla_id"] = out.apply(lambda x: f"local-cas-{int(x['seccion'])}-{x['tipo_casilla']}", axis=1)
    return out.reset_index(drop=True), mapping


def _surname_in_range(surname: str, start: Optional[str], end: Optional[str]) -> bool:
    s = _key(surname)
    if not s:
        return False
    lo = _key(start) or "A"
    hi = _key(end) or "ZZZZZZZZ"
    return lo <= s <= hi


def assign_records_to_booths(normalized: pd.DataFrame, booths: pd.DataFrame) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame()
    rows: List[Dict[str, Any]] = []
    for idx, rec in normalized.iterrows():
        section = rec.get("seccion")
        municipality = _key(rec.get("municipio"))
        promoted = rec.get("promovido_normalizado")
        parent = rec.get("superior_directo")
        explicit = _clean(rec.get("casilla_original")) if "casilla_original" in normalized.columns else None
        surname = rec.get("apellido_paterno") if "apellido_paterno" in normalized.columns else None
        locality = _key(rec.get("localidad"))
        candidates = booths[booths["seccion"].astype(str) == str(section)].copy() if not booths.empty else pd.DataFrame()
        if municipality and not candidates.empty and "municipio" in candidates:
            m = candidates[candidates["municipio"].fillna("").isin(["", municipality])]
            if not m.empty:
                candidates = m

        assigned = None
        status = "PENDIENTE"
        reason = "SIN_CATALOGO"
        if candidates.empty:
            reason = "SECCION_SIN_CASILLAS_CATALOGADAS"
        elif explicit:
            ex = _key(explicit)
            m = candidates[candidates["clave_casilla"].fillna("").map(_key) == ex]
            if len(m) == 1:
                assigned = m.iloc[0]
                status, reason = "CONFIRMADA", "CASILLA_EXPLICITA_EN_EXCEL"
            else:
                reason = "CASILLA_EXPLICITA_NO_COINCIDE_CATALOGO"
        elif len(candidates) == 1:
            assigned = candidates.iloc[0]
            status, reason = "AUTOMATICA", "UNICA_CASILLA_EN_SECCION"
        else:
            extra = candidates[candidates["tipo_casilla"].fillna("").str.startswith("E")]
            if locality and not extra.empty:
                m = extra[extra["localidad"].fillna("") == locality]
                if len(m) == 1:
                    assigned = m.iloc[0]
                    status, reason = "SUGERIDA", "LOCALIDAD_COINCIDE_EXTRAORDINARIA"
            if assigned is None and surname:
                ordinary = candidates[~candidates["tipo_casilla"].fillna("").str.startswith("E")]
                matches = ordinary[ordinary.apply(lambda b: _surname_in_range(surname, b.get("apellido_desde"), b.get("apellido_hasta")), axis=1)]
                if len(matches) == 1:
                    assigned = matches.iloc[0]
                    status, reason = "SUGERIDA", "RANGO_ALFABETICO"
                elif len(matches) > 1:
                    reason = "RANGO_ALFABETICO_AMBIGUO"
                else:
                    reason = "FALTAN_DATOS_PARA_DETERMINAR_CASILLA"
            elif assigned is None:
                reason = "FALTAN_DATOS_PARA_DETERMINAR_CASILLA"

        rows.append({
            "registro_idx": idx,
            "archivo_origen": rec.get("archivo_origen"),
            "estructura_origen": rec.get("estructura_origen"),
            "promovido": promoted,
            "coordinador_directo": parent,
            "seccion": section,
            "municipio": municipality,
            "casilla_id": None if assigned is None else assigned.get("casilla_id"),
            "clave_casilla": None if assigned is None else assigned.get("clave_casilla"),
            "tipo_casilla": None if assigned is None else assigned.get("tipo_casilla"),
            "estado_asignacion": status,
            "criterio_asignacion": reason,
        })
    return pd.DataFrame(rows)


def booth_summary(assignments: pd.DataFrame, responsibilities: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if assignments.empty:
        return pd.DataFrame()
    a = assignments[assignments["casilla_id"].notna()].copy()
    if a.empty:
        return pd.DataFrame()
    grouped = a.groupby(["casilla_id", "clave_casilla", "seccion", "municipio"], dropna=False)
    rows: List[Dict[str, Any]] = []
    for keys, g in grouped:
        casilla_id, clave, section, muni = keys
        counts = g["coordinador_directo"].dropna().value_counts()
        top_coord = counts.index[0] if not counts.empty else None
        top_count = int(counts.iloc[0]) if not counts.empty else 0
        formal = None
        if isinstance(responsibilities, pd.DataFrame) and not responsibilities.empty:
            m = responsibilities[(responsibilities["tipo_territorio"] == "CASILLA") & (responsibilities["territorio_id"] == casilla_id) & (responsibilities["activo"] == True)]
            if not m.empty:
                formal = m.iloc[-1].get("responsable_nombre")
        rows.append({
            "casilla_id": casilla_id,
            "clave_casilla": clave,
            "seccion": section,
            "municipio": muni,
            "promovidos": int(g["promovido"].nunique()),
            "coordinadores_con_promovidos": int(g["coordinador_directo"].dropna().nunique()),
            "coordinador_mayor_estructura": top_coord,
            "promovidos_coordinador_top": top_count,
            "responsable_formal": formal,
            "coincide_responsable_top": None if not formal or not top_coord else formal == top_coord,
        })
    return pd.DataFrame(rows).sort_values(["municipio", "seccion", "clave_casilla"], na_position="last")


def parse_geojson(data: bytes) -> Dict[str, Any]:
    return json.loads(data.decode("utf-8"))
