from app.database import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    tipo_pessoa = db.Column(db.String(20), default="Pessoa jurídica")
    razao_social = db.Column(db.String(150), nullable=False)
    nome_fantasia = db.Column(db.String(150))
    cpf_cnpj = db.Column(db.String(25), unique=True, nullable=False)
    inscricao_estadual = db.Column(db.String(30))
    situacao = db.Column(db.String(20), default="Ativo")
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    cep = db.Column(db.String(15))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(10))
    observacoes = db.Column(db.Text)
    data_cadastro = db.Column(db.String(20), default="14/08/2022")
    ultima_atualizacao = db.Column(db.String(40), default="12/06/2025 às 16:42")

    @property
    def iniciais(self) -> str:
        palavras = (self.razao_social or "").strip().split()
        if not palavras:
            return ""
        if len(palavras) == 1:
            return palavras[0][:2].upper()
        return (palavras[0][0] + palavras[1][0]).upper()

    @property
    def endereco_completo_formatado(self) -> str:
        partes = []

        if self.endereco and self.numero:
            partes.append(f"{self.endereco}, {self.numero}")
        elif self.endereco:
            partes.append(self.endereco)

        if self.bairro:
            partes.append(self.bairro)

        if self.cidade and self.estado:
            partes.append(f"{self.cidade}/{self.estado}")
        elif self.cidade:
            partes.append(self.cidade)
        elif self.estado:
            partes.append(self.estado)

        if self.cep:
            partes.append(self.cep)

        return " · ".join(partes)

    def __repr__(self) -> str:
        return f"<Cliente {self.codigo} - {self.razao_social}>"

