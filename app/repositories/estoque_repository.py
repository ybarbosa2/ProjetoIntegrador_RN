import re
from typing import List, Optional, Tuple

from app.database import db
from app.models.material import Material, MovimentacaoEstoque


def _chave_cronologica_movimentacao(mov: MovimentacaoEstoque) -> Tuple[int, int, int, int, int, int]:
    """Ordena movimentações da mais recente para a mais antiga a partir de data_hora e id."""
    texto = (mov.data_hora or "").strip()
    match_completo = re.search(r"(\d{2})/(\d{2})/(\d{4}).*?(\d{2}):(\d{2})", texto)
    if match_completo:
        dia, mes, ano, hora, minuto = (int(g) for g in match_completo.groups())
        return (ano, mes, dia, hora, minuto, mov.id or 0)

    match_hoje = re.search(r"Hoje.*?(\d{2}):(\d{2})", texto, re.IGNORECASE)
    if match_hoje:
        hora, minuto = (int(g) for g in match_hoje.groups())
        return (9999, 12, 31, hora, minuto, mov.id or 0)

    return (0, 0, 0, 0, 0, mov.id or 0)


class EstoqueRepository:
    """Camada de acesso a dados para Materiais e Movimentações de Estoque."""

    @staticmethod
    def listar_todos(
        busca: Optional[str] = None,
        categoria: Optional[str] = None,
    ) -> List[Material]:
        query = Material.query

        if categoria and categoria not in ("Todas", "Todas as categorias", "todas", ""):
            query = query.filter(Material.categoria == categoria)

        if busca and busca.strip():
            termo = f"%{busca.strip()}%"
            query = query.filter(
                db.or_(
                    Material.codigo.ilike(termo),
                    Material.descricao.ilike(termo),
                    Material.subtitulo.ilike(termo),
                )
            )

        return query.order_by(Material.codigo.desc()).all()

    @staticmethod
    def buscar_por_id(material_id: int) -> Optional[Material]:
        return db.session.get(Material, material_id)

    @staticmethod
    def buscar_por_codigo(codigo: str) -> Optional[Material]:
        if not codigo or not codigo.strip():
            return None
        return Material.query.filter(
            db.func.upper(Material.codigo) == codigo.strip().upper()
        ).first()

    @staticmethod
    def gerar_proximo_codigo() -> str:
        codigos = [row[0] for row in db.session.query(Material.codigo).all() if row[0]]
        maior_numero = 0
        for cod in codigos:
            match = re.search(r"(\d+)$", cod)
            if match:
                maior_numero = max(maior_numero, int(match.group(1)))
        return f"MAT-{maior_numero + 1:04d}"

    @staticmethod
    def listar_ultimas_movimentacoes(limite: int = 10) -> List[MovimentacaoEstoque]:
        todas = MovimentacaoEstoque.query.all()
        ordenadas = sorted(todas, key=_chave_cronologica_movimentacao, reverse=True)
        return ordenadas[:limite]

    @staticmethod
    def listar_movimentacoes_por_material(material_id: int) -> List[MovimentacaoEstoque]:
        movs = MovimentacaoEstoque.query.filter_by(material_id=material_id).all()
        return sorted(movs, key=_chave_cronologica_movimentacao, reverse=True)

    @staticmethod
    def salvar(material: Material) -> Material:
        db.session.add(material)
        db.session.commit()
        return material

    @staticmethod
    def salvar_movimentacao(movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque:
        db.session.add(movimentacao)
        db.session.commit()
        return movimentacao

    @staticmethod
    def excluir(material: Material) -> None:
        db.session.delete(material)
        db.session.commit()

    @staticmethod
    def contar_todos() -> int:
        return Material.query.count()

    @staticmethod
    def contar_alertas_estoque() -> int:
        return Material.query.filter(
            db.or_(Material.disponivel <= 0, Material.disponivel < Material.minimo)
        ).count()

    @staticmethod
    def contar_movimentacoes() -> int:
        return MovimentacaoEstoque.query.count()

    @staticmethod
    def contar_categorias_distintas() -> int:
        return db.session.query(db.func.count(db.func.distinct(Material.categoria))).scalar() or 0

    @staticmethod
    def calcular_valor_total_estoque() -> float:
        total = db.session.query(
            db.func.sum(Material.disponivel * Material.custo_unitario)
        ).scalar()
        return float(total or 0.0)
