from datetime import date, datetime, timedelta
import re
from typing import List, Optional

from app.database import db
from app.models.cliente import Cliente
from app.models.ordem_servico import OrdemServico


def _converter_data_br(texto: Optional[str]) -> Optional[date]:
    """Converte string DD/MM/YYYY em objeto date com segurança."""
    if not texto or not texto.strip():
        return None
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


class OsRepository:
    """Camada de acesso a dados para Ordens de Serviço."""

    @staticmethod
    def listar_todas(
        busca: Optional[str] = None,
        status: Optional[str] = None,
        cliente_id: Optional[int | str] = None,
        periodo: Optional[str] = None,
    ) -> List[OrdemServico]:
        query = OrdemServico.query.join(Cliente, OrdemServico.cliente_id == Cliente.id)

        if status and status not in ("Todos", "todos", ""):
            query = query.filter(OrdemServico.status == status)

        if cliente_id is not None and str(cliente_id).strip() not in ("", "Todos", "todos"):
            try:
                cid = int(cliente_id)
                query = query.filter(OrdemServico.cliente_id == cid)
            except (TypeError, ValueError):
                pass

        if busca and busca.strip():
            termo_limpo = busca.strip().lstrip("#")
            termo = f"%{termo_limpo}%"
            query = query.filter(
                db.or_(
                    OrdemServico.numero.ilike(termo),
                    Cliente.razao_social.ilike(termo),
                    Cliente.nome_fantasia.ilike(termo),
                    OrdemServico.titulo_resumo.ilike(termo),
                    OrdemServico.tipo_servico.ilike(termo),
                    OrdemServico.descricao_detalhada.ilike(termo),
                )
            )

        ordens = query.order_by(OrdemServico.numero.desc(), OrdemServico.id.desc()).all()

        periodo_norm = (periodo or "sempre").strip().lower()
        if periodo_norm in ("", "sempre", "todos", "todo o período"):
            return ordens

        hoje = datetime.now().date()
        dias_map = {"7d": 7, "15d": 15, "30d": 30, "90d": 90}

        if periodo_norm in dias_map:
            data_limite = hoje - timedelta(days=dias_map[periodo_norm])
            return [
                os_item
                for os_item in ordens
                if (dt := _converter_data_br(os_item.data_abertura)) is not None
                and dt >= data_limite
            ]

        if periodo_norm == "ano":
            return [
                os_item
                for os_item in ordens
                if (dt := _converter_data_br(os_item.data_abertura)) is not None
                and dt.year == hoje.year
            ]

        return ordens

    @staticmethod
    def buscar_por_id(os_id: int) -> Optional[OrdemServico]:
        return db.session.get(OrdemServico, os_id)

    @staticmethod
    def buscar_por_numero(numero: str) -> Optional[OrdemServico]:
        if not numero or not numero.strip():
            return None
        normalizado = numero.strip().lstrip("#").upper()
        return OrdemServico.query.filter(
            db.func.upper(OrdemServico.numero) == normalizado
        ).first()

    @staticmethod
    def gerar_proximo_numero() -> str:
        numeros = [row[0] for row in db.session.query(OrdemServico.numero).all() if row[0]]
        maior_numero = 0
        for num in numeros:
            match = re.search(r"(\d+)$", num)
            if match:
                maior_numero = max(maior_numero, int(match.group(1)))
        return f"OS-{maior_numero + 1:04d}"

    @staticmethod
    def contar_todas() -> int:
        return OrdemServico.query.count()

    @staticmethod
    def contar_ativas() -> int:
        return OrdemServico.query.filter(
            OrdemServico.status.notin_(["Concluída", "Cancelada"])
        ).count()

    @staticmethod
    def contar_em_andamento() -> int:
        return OrdemServico.query.filter_by(status="Em andamento").count()

    @staticmethod
    def salvar(ordem_servico: OrdemServico) -> OrdemServico:
        db.session.add(ordem_servico)
        db.session.commit()
        return ordem_servico

    @staticmethod
    def excluir(ordem_servico: OrdemServico) -> None:
        db.session.delete(ordem_servico)
        db.session.commit()


OSRepository = OsRepository
