from typing import List, Optional

from app.models.cliente import Cliente


class ClienteRepository:
    """Camada de acesso a dados para Clientes."""

    @staticmethod
    def listar_todos() -> List[Cliente]:
        return Cliente.query.order_by(Cliente.id.asc()).all()

    @staticmethod
    def buscar_por_id(cliente_id: int) -> Optional[Cliente]:
        return db_get_cliente(cliente_id)

    @staticmethod
    def contar_todos() -> int:
        return Cliente.query.count()

    @staticmethod
    def contar_ativos() -> int:
        return Cliente.query.filter_by(situacao="Ativo").count()


def db_get_cliente(cliente_id: int) -> Optional[Cliente]:
    from app.database import db

    return db.session.get(Cliente, cliente_id)

