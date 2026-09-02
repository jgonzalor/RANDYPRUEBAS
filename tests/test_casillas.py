import pandas as pd
from core.casillas import assign_records_to_booths, booth_summary


def base_record(section=100, surname=None, locality=None):
    return pd.DataFrame([{
        "promovido_normalizado":"PERSONA UNO","superior_directo":"COORDINADOR A","seccion":section,"municipio":"AHOME",
        "apellido_paterno":surname,"localidad":locality,"archivo_origen":"x.xlsx","estructura_origen":"E1","casilla_original":None,
    }])


def test_unique_booth_assigns_automatically():
    booths=pd.DataFrame([{"casilla_id":"b1","seccion":100,"municipio":"AHOME","tipo_casilla":"B","clave_casilla":"100 B","apellido_desde":None,"apellido_hasta":None,"localidad":None}])
    out=assign_records_to_booths(base_record(),booths)
    assert out.iloc[0]["casilla_id"]=="b1"
    assert out.iloc[0]["estado_asignacion"]=="AUTOMATICA"


def test_multiple_booths_without_surname_stays_pending():
    booths=pd.DataFrame([
        {"casilla_id":"b1","seccion":100,"municipio":"AHOME","tipo_casilla":"B","clave_casilla":"100 B","apellido_desde":"A","apellido_hasta":"M","localidad":None},
        {"casilla_id":"b2","seccion":100,"municipio":"AHOME","tipo_casilla":"C1","clave_casilla":"100 C1","apellido_desde":"N","apellido_hasta":"Z","localidad":None},
    ])
    out=assign_records_to_booths(base_record(),booths)
    assert pd.isna(out.iloc[0]["casilla_id"])
    assert out.iloc[0]["estado_asignacion"]=="PENDIENTE"


def test_booth_summary_identifies_top_coordinator():
    assignments=pd.DataFrame([
        {"casilla_id":"b1","clave_casilla":"100 B","seccion":100,"municipio":"AHOME","promovido":"P1","coordinador_directo":"C1"},
        {"casilla_id":"b1","clave_casilla":"100 B","seccion":100,"municipio":"AHOME","promovido":"P2","coordinador_directo":"C1"},
        {"casilla_id":"b1","clave_casilla":"100 B","seccion":100,"municipio":"AHOME","promovido":"P3","coordinador_directo":"C2"},
    ])
    s=booth_summary(assignments)
    assert s.iloc[0]["coordinador_mayor_estructura"]=="C1"
    assert s.iloc[0]["promovidos_coordinador_top"]==2
