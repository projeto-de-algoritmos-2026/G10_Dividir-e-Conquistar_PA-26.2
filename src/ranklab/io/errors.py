"""Tipo de erro de validação do RankLab.

Todos os erros emitidos pelos leitores de IO usam ``RankLabError``, que
carrega o nome do arquivo, o caminho do campo (opcional) e o motivo, no
formato exigido pelo contrato de dados:

    ``{filename}: {field_path}: {reason}``

ou, quando ``field_path`` é omitido:

    ``{filename}: {reason}``
"""

from __future__ import annotations


class RankLabError(Exception):
    """Erro de leitura ou validação de um arquivo RankLab.

    Parâmetros
    ----------
    filename:
        Nome ou caminho do arquivo que originou o erro.
    reason:
        Descrição legível do problema encontrado.
    field_path:
        Caminho pontilhado/indexado até o campo problemático,
        por exemplo ``"items[1].values.custo"``.  Opcional.
    """

    def __init__(self, filename: str, reason: str, field_path: str | None = None) -> None:
        self.filename = filename
        self.reason = reason
        self.field_path = field_path
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.field_path:
            return f"{self.filename}: {self.field_path}: {self.reason}"
        return f"{self.filename}: {self.reason}"
