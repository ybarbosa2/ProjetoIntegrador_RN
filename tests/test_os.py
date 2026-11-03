import pytest

from app import create_app
from app.database import db
from app.models.cliente import Cliente
from app.models.material import Material
from app.models.ordem_servico import OrdemServico
from app.seed import seed_database
from app.services.calculadora_orcamento_service import CalculadoraOrcamentoService
from app.services.os_service import OsService


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
def os_service():
    return OsService()


def test_deve_bloquear_geracao_os_sem_cliente(app, os_service):
    """CT03 / RF03 / RN03: Deve bloquear criação de Ordem de Serviço quando cliente não for selecionado."""
    with app.app_context():
        with pytest.raises(ValueError, match="Cliente obrigatório não selecionado"):
            os_service.criar_ordem_servico(
                {
                    "cliente_id": None,
                    "tipo_servico": "Manutenção industrial",
                    "descricao_detalhada": "Reparo de solda em suporte metálico",
                    "valor_mao_de_obra": 1500.00,
                }
            )


def test_deve_criar_os_com_materiais_e_baixar_estoque(app, os_service):
    """US03 / RF03 / RF04: Cria O.S. vinculada a cliente válido, gera número exclusivo e baixa saldo do estoque."""
    with app.app_context():
        cliente = Cliente.query.filter_by(codigo="CLI-0248").first()
        material = Material.query.filter_by(codigo="MAT-0090").first()  # Saldo inicial: 46
        assert cliente is not None
        assert material is not None
        saldo_anterior = material.disponivel

        nova_os = os_service.criar_ordem_servico(
            dados={
                "cliente_id": cliente.id,
                "tipo_servico": "Fabricação de estrutura metálica",
                "titulo_resumo": "Suporte aéreo para tubulação",
                "descricao_detalhada": "Fabricação de suporte em cantoneira estrutural.",
                "responsavel": "Carlos Mendes",
                "valor_mao_de_obra": 2400.00,
            },
            lista_materiais=[
                {"material_id": material.id, "quantidade": 2},
            ],
        )

        assert nova_os.id is not None
        assert nova_os.numero == "OS-1049"
        assert len(nova_os.itens) == 1
        assert nova_os.valor_materiais == 220.00  # 2 * 110.00
        assert nova_os.valor_total == 2620.00

        material_atualizado = db.session.get(Material, material.id)
        assert material_atualizado.disponivel == saldo_anterior - 2


def test_deve_gerar_orcamento_a_partir_da_os(app):
    """CT06 / US04 / RF05: Verifica se CalculadoraOrcamentoService consolida cliente, itens e valor total da O.S."""
    with app.app_context():
        os_1048 = OrdemServico.query.filter_by(numero="OS-1048").first()
        assert os_1048 is not None

        orcamento = CalculadoraOrcamentoService.gerar_dados_orcamento(os_1048)

        assert orcamento["codigo_orcamento"] == "ORC-1048"
        assert orcamento["numero_os"] == "OS-1048"
        assert orcamento["cliente"]["razao_social"] == "Construtora Horizonte Ltda."
        assert orcamento["cliente"]["cpf_cnpj"] == "18.420.331/0001-06"
        assert len(orcamento["itens"]) == 2
        assert orcamento["valor_materiais"] == 2747.40
        assert orcamento["valor_mao_de_obra"] == 8500.00
        assert orcamento["valor_total"] == 11247.40
