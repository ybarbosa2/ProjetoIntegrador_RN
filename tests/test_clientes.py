import pytest

from app import create_app
from app.database import db
from app.models.cliente import Cliente
from app.seed import seed_database
from app.services.cliente_service import ClienteService


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SKIP_AUTO_SEED": True,
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def cliente_service():
    return ClienteService()


def test_deve_bloquear_cadastro_cnpj_duplicado(app, cliente_service):
    """RN01 / CT05: Deve bloquear cadastro de cliente cujo CNPJ já exista no sistema."""
    with app.app_context():
        dados_duplicados = {
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Construtora Horizonte Filial Ltda.",
            "nome_fantasia": "Horizonte Filial",
            "cpf_cnpj": "18.420.331/0001-06",  # CNPJ já pertencente ao CLI-0248
            "telefone": "(15) 3312-8499",
            "email": "filial@horizonte.com.br",
        }

        with pytest.raises(ValueError, match="Este CNPJ já está cadastrado no sistema"):
            cliente_service.cadastrar_cliente(dados_duplicados)


def test_deve_cadastrar_cliente_com_dados_validos(app, cliente_service):
    """RF01 / CT01: Deve cadastrar cliente válido gerando código sequencial CLI-XXXX."""
    with app.app_context():
        dados_validos = {
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Usinagem Precisão Sorocaba Ltda.",
            "nome_fantasia": "Precisão Usinagem",
            "cpf_cnpj": "63.812.509/0001-47",
            "inscricao_estadual": "669.110.220.330",
            "situacao": "Ativo",
            "telefone": "(15) 3219-4500",
            "email": "contato@precisaousinagem.com.br",
            "cep": "18087-100",
            "endereco": "Av. Independência",
            "numero": "2500",
            "bairro": "Éden",
            "cidade": "Sorocaba",
            "estado": "SP",
        }

        novo_cliente = cliente_service.cadastrar_cliente(dados_validos)

        assert novo_cliente is not None
        assert novo_cliente.id is not None
        assert novo_cliente.codigo == "CLI-0249"

        persistido = Cliente.query.filter_by(codigo="CLI-0249").first()
        assert persistido is not None
        assert persistido.razao_social == "Usinagem Precisão Sorocaba Ltda."
        assert persistido.cpf_cnpj == "63.812.509/0001-47"


def test_deve_bloquear_cadastro_sem_campos_obrigatorios(app, cliente_service):
    """UC03-E2: Deve lançar ValueError quando razão social ou CPF/CNPJ não forem informados."""
    with app.app_context():
        with pytest.raises(ValueError):
            cliente_service.cadastrar_cliente(
                {"razao_social": "", "cpf_cnpj": "12.345.678/0001-95"}
            )

        with pytest.raises(ValueError):
            cliente_service.cadastrar_cliente(
                {"razao_social": "Empresa Sem Documento Ltda.", "cpf_cnpj": ""}
            )
