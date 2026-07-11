"""La skill de notas escribe dentro de la carpeta permitida y respeta la jaula."""
from __future__ import annotations

from core.contexto import Contexto

import skills.notas as notas


def test_nota_escribe_dentro_de_la_jaula(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(notas, "raices_de", lambda _skill: [str(tmp_path)])
    skill = notas.SkillNota()
    resultado = skill.ejecutar({"texto": "comprar leche"}, Contexto())
    assert resultado.ok
    assert (tmp_path / "notas.txt").read_text(encoding="utf-8").strip() == "comprar leche"


def test_nota_vacia_no_escribe(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(notas, "raices_de", lambda _skill: [str(tmp_path)])
    skill = notas.SkillNota()
    resultado = skill.ejecutar({"texto": "   "}, Contexto())
    assert not resultado.ok
    assert not (tmp_path / "notas.txt").exists()


def test_nota_sin_carpeta_configurada_falla_amablemente(monkeypatch) -> None:
    monkeypatch.setattr(notas, "raices_de", lambda _skill: [])
    skill = notas.SkillNota()
    resultado = skill.ejecutar({"texto": "algo"}, Contexto())
    assert not resultado.ok
    assert "permisos.yaml" in resultado.mensaje
