"""Estados de residencia: el asistente no debe reservar la GPU 24/7.
Se testea SIN GPU: se simula un recurso caro con un sleep.
"""
from __future__ import annotations

import time

from core.residencia import Estado, Residencia


class ModeloFalso:
    """Simula Whisper: caro de cargar, barato de usar."""

    def __init__(self, demora: float = 0.2) -> None:
        self.demora = demora
        self.cargas = 0
        self.descargas = 0

    def cargar(self):
        time.sleep(self.demora)
        self.cargas += 1
        return f"modelo-{self.cargas}"

    def descargar(self) -> None:
        self.descargas += 1


def test_arranca_dormido() -> None:
    m = ModeloFalso()
    r = Residencia(m.cargar, m.descargar)
    assert r.estado == Estado.DORMIDO
    assert m.cargas == 0, "no debe tocar la GPU antes del wake word"


def test_warm_up_carga_mientras_el_usuario_habla() -> None:
    """El truco central: al disparar el wake word la carga arranca en paralelo.
    Para cuando el usuario termina de hablar, el modelo ya está caliente."""
    m = ModeloFalso(demora=0.3)
    r = Residencia(m.cargar, m.descargar)

    r.despertar()                      # dispara el wake word
    assert r.estado == Estado.DESPERTANDO

    time.sleep(0.35)                   # el usuario dice el comando (tarda más que la carga)

    t0 = time.monotonic()
    recurso = r.obtener()              # ya debería estar listo: espera ~0
    espera = time.monotonic() - t0

    assert recurso == "modelo-1"
    assert espera < 0.1, f"el warm-up no sirvió: esperó {espera:.2f}s"
    assert r.estado == Estado.ACTIVO


def test_obtener_espera_si_el_usuario_fue_muy_rapido() -> None:
    """Si el comando llega antes de que termine la carga, obtener() espera. Nunca falla."""
    m = ModeloFalso(demora=0.3)
    r = Residencia(m.cargar, m.descargar)
    r.despertar()
    assert r.obtener() == "modelo-1"   # bloquea hasta que carga
    assert r.estado == Estado.ACTIVO


def test_enfria_y_vuelve_a_dormir() -> None:
    m = ModeloFalso(demora=0.05)
    r = Residencia(m.cargar, m.descargar, gracia_s=0.15)
    r.despertar()
    r.obtener()

    r.enfriar()
    assert r.estado == Estado.ENFRIANDO
    assert m.descargas == 0            # todavía no: está en la ventana de gracia

    time.sleep(0.3)
    assert r.estado == Estado.DORMIDO
    assert m.descargas == 1, "no liberó la VRAM"


def test_segundo_comando_dentro_de_la_gracia_no_recarga() -> None:
    """Si hablás de nuevo antes de que expire la gracia, el modelo sigue caliente:
    latencia cero y una sola carga."""
    m = ModeloFalso(demora=0.05)
    r = Residencia(m.cargar, m.descargar, gracia_s=0.5)

    r.despertar()
    r.obtener()
    r.enfriar()

    time.sleep(0.1)                    # dentro de la ventana
    r.despertar()
    assert r.obtener() == "modelo-1"
    assert m.cargas == 1, "recargó el modelo sin necesidad"
    assert r.estado == Estado.ACTIVO


def test_despertar_dos_veces_no_carga_dos_veces() -> None:
    """El wake word puede dispararse dos veces seguidas: no debe duplicar la carga."""
    m = ModeloFalso(demora=0.2)
    r = Residencia(m.cargar, m.descargar)
    r.despertar()
    r.despertar()
    r.obtener()
    assert m.cargas == 1


def test_detener_libera_todo() -> None:
    m = ModeloFalso(demora=0.05)
    r = Residencia(m.cargar, m.descargar, gracia_s=99)
    r.despertar()
    r.obtener()
    r.detener()
    assert r.estado == Estado.DORMIDO
    assert m.descargas == 1
