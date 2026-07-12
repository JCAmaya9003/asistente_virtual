"""La rejilla de parámetros es lo que da variedad al dataset sintético."""
from __future__ import annotations

from wakeword.generar import combinaciones


def test_reparte_entre_todas_las_voces() -> None:
    combos = combinaciones(["a.onnx", "b.onnx", "c.onnx"], objetivo=300)
    voces = {c[0] for c in combos}
    assert voces == {"a.onnx", "b.onnx", "c.onnx"}


def test_devuelve_la_cantidad_pedida() -> None:
    assert len(combinaciones(["v.onnx"], objetivo=57)) == 57


def test_hay_variedad_real_de_parametros() -> None:
    """El punto de todo: si todas las muestras tuvieran los mismos parámetros, el
    detector sería frágil."""
    combos = combinaciones(["v.onnx"], objetivo=200)
    assert len({c[1] for c in combos}) > 1, "no varía la velocidad"
    assert len({c[2] for c in combos}) > 1, "no varía la expresividad"
    assert len({c[3] for c in combos}) > 1, "no varía el ritmo"
    assert len({c[4] for c in combos}) > 1, "no varía el volumen"


def test_sin_voces_no_genera_nada() -> None:
    assert combinaciones([], objetivo=100) == []


def test_es_determinista() -> None:
    """Mismo input, mismo dataset: los experimentos deben ser reproducibles."""
    a = combinaciones(["x.onnx", "y.onnx"], 50)
    b = combinaciones(["x.onnx", "y.onnx"], 50)
    assert a == b
