from typing import List, Optional

from app.database import db
from app.models.ordem_servico import OrdemServico


class OSRepository:
    """Camada de acesso a dados para Ordens de Serviço."""

    @staticmethod
    def listar_todas() -> List[OrdemServico]:
        return OrdemServico.query.order_by(OrdemServico.id.asc()).all()

    @staticmethod
    def buscar_por_id(os_id: int) -> Optional[OrdemServico]:
        return db.session.get(OrdemServico, os_id)

    @staticmethod
    def contar_todas() -> int:
        return OrdemServico.query.count()

    @staticmethod
    def contar_ativas() -> int:
        return OrdemServico.query.filter(OrdemServico.status != "Concluída").count()

    @staticmethod
    def contar_em_andamento() -> int:
        return OrdemServico.query.filter_by(status="Em andamento").count()

