"""La configuración de la tecla debe traducirse bien, y fallar claro si es inválida."""
from __future__ import annotations

import pytest

pytest.importorskip("pynput", reason="pynput no instalado (llega en la v3)")

from adapters.hotkey import parsear_tecla   # noqa: E402


def test_tecla_especial() -> None:
    from pynput import keyboard
    assert parsear_tecla("ctrl_r") == keyboard.Key.ctrl_r


def test_tecla_de_funcion() -> None:
    from pynput import keyboard
    assert parsear_tecla("f9") == keyboard.Key.f9


def test_caracter_simple() -> None:
    assert parsear_tecla("k") is not None


def test_tecla_invalida_falla_claro() -> None:
    with pytest.raises(ValueError, match="no reconocida"):
        parsear_tecla("tecla_que_no_existe")
