from typing import Dict, List

from app.models.ordem_servico import OrdemServico
from app.repositories.os_repository import OSRepository


class OSService:
    """Regras de negócio do módulo de Ordens de Serviço."""

    def __init__(self, repository: OSRepository | None = None) -> None:
        self.repository = repository or OSRepository()

    def listar_ordens(self) -> List[OrdemServico]:
        return self.repository.listar_todas()

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.repository.contar_todas(),
            "ativas": self.repository.contar_ativas(),
            "em_andamento": self.repository.contar_em_andamento(),
        }

