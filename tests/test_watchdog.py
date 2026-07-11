"""El watchdog es lo que hace que el asistente sobreviva al uso real.
Se testea SIN micrófono: la detección de 'stream muerto' es una función pura.
"""
from __future__ import annotations

import time

from core.watchdog import Watchdog, microfono_mudo, varianza


# --- detección de stream muerto ---------------------------------------------

def test_stream_muerto_entrega_ceros() -> None:
    """El síntoma real: el dispositivo se desconectó y el stream entrega ceros
    exactos, sin lanzar ninguna excepción."""
    assert microfono_mudo([0.0] * 1600)


def test_silencio_real_no_es_stream_muerto() -> None:
    """Un cuarto en silencio tiene ruido de fondo: varianza pequeña pero > 0.
    Distinguir esto de un stream muerto es TODO el truco del watchdog."""
    ruido = [0.0001 * ((-1) ** i) for i in range(1600)]
    assert not microfono_mudo(ruido)


def test_habla_no_es_stream_muerto() -> None:
    assert not microfono_mudo([0.4, -0.3, 0.5, -0.45] * 400)


def test_varianza_de_constante_es_cero() -> None:
    """Una señal DC constante (no solo ceros) también es un stream muerto.
    Se compara contra el epsilon, no con ==: en flotantes el cálculo da ~1e-30, no 0.0.
    """
    assert microfono_mudo([0.7] * 100)


def test_varianza_de_vacio_es_cero() -> None:
    assert varianza([]) == 0.0


# --- ciclo del watchdog ------------------------------------------------------

def test_repara_cuando_el_microfono_esta_mudo() -> None:
    reparaciones = []
    wd = Watchdog(
        comprobar=lambda: False,                     # micrófono siempre mudo
        reparar=lambda: reparaciones.append(1),
        intervalo_s=0.05,
    )
    wd.iniciar()
    time.sleep(0.2)
    wd.detener()
    assert reparaciones, "el watchdog no reabrió el stream"
    assert wd.fallos > 0


def test_no_repara_si_esta_sano() -> None:
    reparaciones = []
    wd = Watchdog(
        comprobar=lambda: True,
        reparar=lambda: reparaciones.append(1),
        intervalo_s=0.05,
    )
    wd.iniciar()
    time.sleep(0.2)
    wd.detener()
    assert not reparaciones
    assert wd.fallos == 0


def test_un_error_al_comprobar_no_tumba_el_watchdog() -> None:
    """El watchdog JAMÁS debe matar al proceso que vigila."""
    def comprobar_roto():
        raise RuntimeError("dispositivo desapareció")

    wd = Watchdog(comprobar=comprobar_roto, reparar=lambda: None, intervalo_s=0.05)
    wd.iniciar()
    time.sleep(0.15)
    wd.detener()          # si el hilo hubiera muerto, esto no cerraría limpio


def test_late_en_el_audit_log() -> None:
    latidos = []
    wd = Watchdog(
        comprobar=lambda: True,
        reparar=lambda: None,
        latir=lambda: latidos.append(1),
        intervalo_s=0.05,
        latido_cada_s=0,                             # late en cada ciclo
    )
    wd.iniciar()
    time.sleep(0.2)
    wd.detener()
    assert latidos, "el watchdog no escribió ningún latido"
