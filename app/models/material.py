from app.database import db


class Material(db.Model):
    __tablename__ = "materiais"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    descricao = db.Column(db.String(150), nullable=False)
    subtitulo = db.Column(db.String(150), default="Aço carbono laminado a quente")
    categoria = db.Column(db.String(50), nullable=False)
    tipo_material = db.Column(db.String(80), default="Aço carbono")
    unidade = db.Column(db.String(10), nullable=False)
    disponivel = db.Column(db.Float, nullable=False, default=0.0)
    minimo = db.Column(db.Float, nullable=False, default=0.0)
    custo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    localizacao = db.Column(db.String(100))
    controle_lote = db.Column(db.String(50), default="Não utilizado")
    fornecedor = db.Column(db.String(150))
    situacao = db.Column(db.String(20), default="Ativo")
    observacoes = db.Column(db.Text)

    movimentacoes = db.relationship(
        "MovimentacaoEstoque",
        backref="material",
        cascade="all, delete-orphan",
        lazy=True,
    )

    @property
    def status_estoque(self) -> str:
        disponivel = self.disponivel if self.disponivel is not None else 0.0
        minimo = self.minimo if self.minimo is not None else 0.0
        if disponivel <= 0:
            return "Indisponível"
        if disponivel < minimo:
            return "Baixo"
        return "Normal"

    @property
    def quantidade_reposicao(self) -> int:
        disponivel = self.disponivel if self.disponivel is not None else 0.0
        minimo = self.minimo if self.minimo is not None else 0.0
        return max(0, int(minimo - disponivel))

    def __repr__(self) -> str:
        return f"<Material {self.codigo} - {self.descricao}>"


class MovimentacaoEstoque(db.Model):
    __tablename__ = "movimentacoes_estoque"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materiais.id"), nullable=False)
    data_hora = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    descricao_movimentacao = db.Column(db.String(150), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), default="Carlos Mendes")

    def __repr__(self) -> str:
        return f"<MovimentacaoEstoque {self.tipo} ({self.quantidade}) - Material ID {self.material_id}>"

