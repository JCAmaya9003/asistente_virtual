"""Log append-only en JSONL. Es la auditoría de seguridad y la mejor herramienta de debug.
Existe desde el primer commit por diseño, no como agregado posterior.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Auditor:
    def __init__(self, ruta: str | Path = "audit.jsonl") -> None:
        self._ruta = Path(ruta)

    def registrar(self, *, skill: str, params: dict[str, Any], origen: str,
                  resultado: str, motivo: str | None = None) -> None:
        entrada: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "skill": skill,
            "params": params,
            "origen": origen,
            "resultado": resultado,
        }
        if motivo is not None:
            entrada["motivo"] = motivo
        with self._ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

    def latido(self) -> None:
        """Heartbeat para el watchdog (v3). Si el último latido es viejo, el proceso murió."""
        self.registrar(skill="__heartbeat__", params={}, origen="sistema", resultado="ok")
