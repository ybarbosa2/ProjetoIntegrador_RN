from typing import List, Optional

from app.database import db
from app.models.material import Material


class EstoqueRepository:
    """Camada de acesso a dados para Materiais e Movimentações de Estoque."""

    @staticmethod
    def listar_todos() -> List[Material]:
        return Material.query.order_by(Material.id.asc()).all()

    @staticmethod
    def buscar_por_id(material_id: int) -> Optional[Material]:
        return db.session.get(Material, material_id)

    @staticmethod
    def contar_todos() -> int:
        return Material.query.count()

    @staticmethod
    def contar_alertas_estoque() -> int:
        return Material.query.filter(Material.disponivel < Material.minimo).count()

