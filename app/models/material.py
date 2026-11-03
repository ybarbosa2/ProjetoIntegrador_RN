from app.database import db

UNIDADES_EXTENSO = {
    "UN": "Unidade (UN)",
    "M": "Metro (M)",
    "BR": "Barra (BR)",
    "KG": "Quilograma (KG)",
}

UNIDADES_ABREVIADAS = {
    "UN": "un.",
    "M": "m",
    "BR": "br.",
    "KG": "kg",
}


def formatar_quantidade(valor: float | int | None) -> str:
    numero = float(valor or 0.0)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}".rstrip("0").rstrip(".").replace(".", ",")


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

    def registrar_entrada(self, quantidade: float) -> None:
        """Soma quantidade positiva ao saldo disponível do material."""
        qtd = float(quantidade or 0.0)
        if qtd <= 0:
            raise ValueError("A quantidade de entrada deve ser maior que zero.")
        saldo_atual = float(self.disponivel if self.disponivel is not None else 0.0)
        self.disponivel = saldo_atual + qtd

    def registrar_saida(self, quantidade: float) -> None:
        """Subtrai quantidade do saldo disponível, impedindo saldo negativo (RN02)."""
        qtd = float(quantidade or 0.0)
        if qtd <= 0:
            raise ValueError("A quantidade de saída deve ser maior que zero.")
        saldo_atual = float(self.disponivel if self.disponivel is not None else 0.0)
        if qtd > saldo_atual:
            raise ValueError("Saldo insuficiente no estoque")
        self.disponivel = saldo_atual - qtd

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

    @property
    def disponivel_formatado(self) -> str:
        return formatar_quantidade(self.disponivel)

    @property
    def minimo_formatado(self) -> str:
        return formatar_quantidade(self.minimo)

    @property
    def unidade_extenso(self) -> str:
        un = (self.unidade or "UN").upper()
        return UNIDADES_EXTENSO.get(un, un)

    @property
    def unidade_abreviada(self) -> str:
        un = (self.unidade or "UN").upper()
        return UNIDADES_ABREVIADAS.get(un, un.lower())

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

    @property
    def quantidade_formatada(self) -> str:
        return formatar_quantidade(self.quantidade)

    def __repr__(self) -> str:
        return f"<MovimentacaoEstoque {self.tipo} ({self.quantidade}) - Material ID {self.material_id}>"
