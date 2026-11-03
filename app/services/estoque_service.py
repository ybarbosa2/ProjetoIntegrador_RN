from typing import Dict, List

from app.models.material import Material
from app.repositories.estoque_repository import EstoqueRepository


class EstoqueService:
    """Regras de negócio do módulo de Estoque."""

    def __init__(self, repository: EstoqueRepository | None = None) -> None:
        self.repository = repository or EstoqueRepository()

    def listar_materiais(self) -> List[Material]:
        return self.repository.listar_todos()

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.repository.contar_todos(),
            "estoque_baixo": self.repository.contar_alertas_estoque(),
        }

