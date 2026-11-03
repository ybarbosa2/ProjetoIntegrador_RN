from unittest.mock import MagicMock

import pytest

from app import create_app
from app.database import db
from app.models.material import Material
from app.repositories.estoque_repository import EstoqueRepository
from app.seed import seed_database
from app.services.estoque_service import EstoqueService


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


def test_deve_impedir_saldo_negativo_ao_registrar_saida_de_material():
    """CT02 / RN02 / Seção 5.3: Deve lançar ValueError e manter saldo inalterado ao tentar retirar mais que o disponível."""
    peca = Material(
        codigo="MAT-9001",
        descricao="Rolamento Industrial",
        categoria="Consumíveis",
        unidade="UN",
        disponivel=10,
        minimo=5,
        custo_unitario=45.0,
    )
    repositorio_mock = MagicMock(spec=EstoqueRepository)
    service = EstoqueService(repositorio=repositorio_mock)

    with pytest.raises(ValueError, match="Saldo insuficiente no estoque"):
        service.registrar_saida(peca, 15)

    assert peca.disponivel == 10
    repositorio_mock.salvar.assert_not_called()


def test_deve_atualizar_saldo_ao_registrar_entrada_de_material():
    """CT04 / RF02: Peça com saldo 5, registra entrada de 10 unidades e passa a exibir saldo 15."""
    peca = Material(
        codigo="MAT-9002",
        descricao="Disco de Corte 7\"",
        categoria="Consumíveis",
        unidade="UN",
        disponivel=5,
        minimo=10,
        custo_unitario=18.5,
    )

    peca.registrar_entrada(10)

    assert peca.disponivel == 15


def test_deve_atualizar_saldo_ao_salvar_registro_de_entrada_com_mock():
    """Seção 5.4 (Mocks e Stubs): Verifica integração isolada entre EstoqueService e EstoqueRepository via MagicMock."""
    repositorio_mock = MagicMock(spec=EstoqueRepository)
    service = EstoqueService(repositorio_mock)
    peca = Material(
        codigo="MAT-9003",
        descricao="Motor 2CV",
        categoria="Consumíveis",
        unidade="UN",
        disponivel=2,
        minimo=1,
        custo_unitario=950.0,
    )

    service.adicionar_entrada(peca, 5)

    repositorio_mock.salvar.assert_called_once_with(peca)
    assert peca.disponivel == 7


def test_cadastro_material_gera_proximo_codigo_e_movimentacao_inicial(app):
    """Verifica geração automática de MAT-0093 e registro de entrada inicial no banco."""
    with app.app_context():
        service = EstoqueService()
        novo = service.cadastrar_material(
            {
                "descricao": "Chapa galvanizada 2mm",
                "categoria": "Chapas",
                "tipo_material": "Aço galvanizado",
                "unidade": "UN",
                "quantidade_inicial": "30",
                "minimo": "10",
                "custo_unitario": "210,50",
                "fornecedor": "Aços Paulista Distribuidora",
                "localizacao": "Setor A · Estante 05",
            }
        )

        assert novo.id is not None
        assert novo.codigo == "MAT-0093"
        assert novo.disponivel == 30.0
        assert novo.custo_unitario == 210.50
        assert novo.status_estoque == "Normal"

        movs = service.listar_movimentacoes_por_material(novo.id)
        assert len(movs) == 1
        assert movs[0].tipo == "Entrada"
        assert movs[0].quantidade == 30.0
