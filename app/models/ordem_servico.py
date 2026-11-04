from app.database import db


class OrdemServico(db.Model):
    __tablename__ = "ordens_servico"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    data_abertura = db.Column(db.String(20), nullable=False)
    prazo_entrega = db.Column(db.String(20), nullable=True, default="")
    status = db.Column(db.String(30), default="Aberta")
    titulo_resumo = db.Column(db.String(150))
    tipo_servico = db.Column(db.String(150))
    quantidade_servico = db.Column(db.String(50), default="1 conjunto")
    responsavel = db.Column(db.String(100))
    descricao_detalhada = db.Column(db.Text)
    especificacoes_tecnicas = db.Column(db.Text)
    valor_mao_de_obra = db.Column(db.Float, default=0.0)

    cliente = db.relationship(
        "Cliente",
        backref=db.backref("ordens_servico", lazy=True),
    )
    itens = db.relationship(
        "ItemOrdemServico",
        backref="ordem_servico",
        cascade="all, delete-orphan",
        lazy=True,
    )

    @property
    def valor_materiais(self) -> float:
        return float(sum(item.valor_total for item in self.itens))

    @property
    def valor_total(self) -> float:
        mao_de_obra = self.valor_mao_de_obra if self.valor_mao_de_obra is not None else 0.0
        return float(mao_de_obra + self.valor_materiais)

    def __repr__(self) -> str:
        return f"<OrdemServico {self.numero} - {self.status}>"


class ItemOrdemServico(db.Model):
    __tablename__ = "itens_ordem_servico"

    id = db.Column(db.Integer, primary_key=True)
    os_id = db.Column(db.Integer, db.ForeignKey("ordens_servico.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materiais.id"), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)

    material = db.relationship("Material")

    @property
    def valor_total(self) -> float:
        qtd = self.quantidade if self.quantidade is not None else 0.0
        unitario = self.valor_unitario if self.valor_unitario is not None else 0.0
        return float(qtd * unitario)

    def __repr__(self) -> str:
        return f"<ItemOrdemServico OS={self.os_id} Material={self.material_id}>"

