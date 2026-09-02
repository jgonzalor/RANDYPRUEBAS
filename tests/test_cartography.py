import pandas as pd

from core.cartography import build_geojson_with_metrics, enrich_normalized_with_cartography, load_section_catalog


def test_precargada_cartografia_sinaloa():
    cat=load_section_catalog()
    assert len(cat)==3855
    row=cat[cat["seccion"]==316].iloc[0]
    assert row["municipio"]=="AHOME"
    assert int(row["distrito_local"])==3
    assert int(row["distrito_federal"])==2


def test_enrichment_preserves_excel_and_flags_conflict():
    df=pd.DataFrame([{
        "fila_excel":2,"promovido_normalizado":"PERSONA","seccion":316,"municipio":"GUASAVE","estado_validacion":"LISTO"
    }])
    out,inc=enrich_normalized_with_cartography(df)
    assert out.iloc[0]["municipio_excel"]=="GUASAVE"
    assert out.iloc[0]["municipio"]=="AHOME"
    assert int(out.iloc[0]["distrito_local"])==3
    assert out.iloc[0]["estado_validacion"]=="REVISAR"
    assert "MUNICIPIO_CONFLICTO_CARTOGRAFIA" in inc["tipo"].tolist()


def test_geojson_filter_and_metrics():
    metrics=pd.DataFrame([{"numero":316,"promovidos":12,"coordinadores":2,"casillas_catalogadas":3,"promovidos_sin_casilla":4}])
    obj=build_geojson_with_metrics(metrics,[316])
    assert len(obj["features"])==1
    p=obj["features"][0]["properties"]
    assert p["seccion"]==316
    assert p["promovidos"]==12
