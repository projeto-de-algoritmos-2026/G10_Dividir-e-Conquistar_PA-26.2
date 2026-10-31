"""Testes para o tipo RankLabError."""

from ranklab.io.errors import RankLabError


def test_str_with_field_path() -> None:
    err = RankLabError("matriz.json", "valor ausente", "items[1].values.custo")
    assert str(err) == "matriz.json: items[1].values.custo: valor ausente"


def test_str_without_field_path() -> None:
    err = RankLabError("ranking.json", "campo obrigatório ausente: ranking_id")
    assert str(err) == "ranking.json: campo obrigatório ausente: ranking_id"


def test_is_exception() -> None:
    err = RankLabError("f.json", "motivo")
    assert isinstance(err, Exception)


def test_attributes() -> None:
    err = RankLabError("f.json", "motivo", "items[0].item_id")
    assert err.filename == "f.json"
    assert err.reason == "motivo"
    assert err.field_path == "items[0].item_id"


def test_field_path_none_by_default() -> None:
    err = RankLabError("f.json", "motivo")
    assert err.field_path is None
