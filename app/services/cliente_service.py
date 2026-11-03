from typing import Dict, List

from app.models.cliente import Cliente
from app.repositories.cliente_repository import ClienteRepository


class ClienteService:
    """Regras de negócio do módulo de Clientes."""

    def __init__(self, repository: ClienteRepository | None = None) -> None:
        self.repository = repository or ClienteRepository()

    def listar_clientes(self) -> List[Cliente]:
        return self.repository.listar_todos()

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.repository.contar_todos(),
            "ativos": self.repository.contar_ativos(),
        }

