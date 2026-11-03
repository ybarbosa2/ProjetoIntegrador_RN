import pytest

from app import create_app, formatar_moeda
from app.database import db
from app.models.cliente import Cliente
from app.models.material import Material, MovimentacaoEstoque
from app.models.ordem_servico import OrdemServico
from app.seed import seed_database


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
def client(app):
    return app.test_client()


def test_app_initialization_and_seed(app):
    """Verifica se a aplicação inicia, cria o banco em memória e executa o seed fiel ao Figma."""
    with app.app_context():
        assert Cliente.query.count() == 6
        assert Material.query.count() == 5
        assert MovimentacaoEstoque.query.count() == 5
        assert OrdemServico.query.count() == 7

        # Idempotência do seed
        seed_database()
        assert Cliente.query.count() == 6

        # Verificação de propriedades de Cliente (CLI-0248)
        horizonte = Cliente.query.filter_by(codigo="CLI-0248").first()
        assert horizonte is not None
        assert horizonte.iniciais == "CH"
        assert (
            horizonte.endereco_completo_formatado
            == "Av. Eng. Carlos Reinaldo Mendes, 1840 · Alto da Boa Vista · Sorocaba/SP · 18013-280"
        )

        # Verificação de propriedades de Material (MAT-0092 e MAT-0090)
        chapa = Material.query.filter_by(codigo="MAT-0092").first()
        assert chapa is not None
        assert chapa.status_estoque == "Baixo"
        assert chapa.quantidade_reposicao == 12

        cantoneira = Material.query.filter_by(codigo="MAT-0090").first()
        assert cantoneira is not None
        assert cantoneira.status_estoque == "Normal"
        assert cantoneira.quantidade_reposicao == 0

        # Verificação de propriedades de Ordem de Serviço (OS-1048) e filtro moeda
        os_1048 = OrdemServico.query.filter_by(numero="OS-1048").first()
        assert os_1048 is not None
        assert len(os_1048.itens) == 2
        assert round(os_1048.valor_materiais, 2) == 2747.40
        assert round(os_1048.valor_total, 2) == 11247.40
        assert formatar_moeda(os_1048.valor_total) == "R$ 11.247,40"


def test_home_and_main_navigation_routes_return_200(client):
    """Verifica se a rota inicial e as rotas principais dos módulos retornam HTTP 200."""
    response_home = client.get("/")
    assert response_home.status_code == 200
    html_home = response_home.get_data(as_text=True)
    assert "SOLUÇÕES INDUSTRIAIS" in html_home
    assert "Módulo de Clientes" in html_home
    assert "Módulo de Estoque" in html_home
    assert "Módulo de Ordens de Serviço" in html_home

    for rota in ("/clientes", "/estoque", "/os", "/configuracoes"):
        resp = client.get(rota)
        assert resp.status_code == 200, f"Falha na rota {rota}"


def test_rota_configuracoes_e_feature_flags(client):
    """Verifica a tela /configuracoes, exibição da flag ENABLE_FISCAL_MODULE e alternância de flags."""
    resp = client.get("/configuracoes")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "ENABLE_FISCAL_MODULE" in html
    assert "ENABLE_WHATSAPP_NOTIFICATION" in html
    assert "ENABLE_REALTIME_STOCK_CHECK" in html
    assert "Desativado (False)" in html
    assert "R.N. Soluções Industriais" in html

    # Módulo fiscal bloqueado quando ENABLE_FISCAL_MODULE = False
    resp_fiscal_off = client.get("/faturamento", follow_redirects=True)
    assert resp_fiscal_off.status_code == 200
    assert "desativado pela Feature Flag ENABLE_FISCAL_MODULE" in resp_fiscal_off.get_data(
        as_text=True
    )

    # Ativa ENABLE_FISCAL_MODULE via toggle
    resp_toggle_on = client.post(
        "/configuracoes/toggle-flag",
        data={"flag": "ENABLE_FISCAL_MODULE"},
        follow_redirects=True,
    )
    assert resp_toggle_on.status_code == 200
    assert "ENABLE_FISCAL_MODULE alterada para Ativada (True)" in resp_toggle_on.get_data(
        as_text=True
    )

    # Agora /faturamento fica acessível e item aparece na sidebar
    resp_fiscal_on = client.get("/faturamento")
    assert resp_fiscal_on.status_code == 200
    assert "ENABLE_FISCAL_MODULE = True" in resp_fiscal_on.get_data(as_text=True)

    # Tentativa de desativar flag obrigatória RN02 é protegida
    resp_protegida = client.post(
        "/configuracoes/toggle-flag",
        data={"flag": "ENABLE_REALTIME_STOCK_CHECK"},
        follow_redirects=True,
    )
    assert resp_protegida.status_code == 200
    assert "permanece sempre ativa" in resp_protegida.get_data(as_text=True)

    # Reset seed de demonstração
    resp_reset = client.post("/configuracoes/reset-seed", follow_redirects=True)
    assert resp_reset.status_code == 200
    assert "restaurado com os dados oficiais" in resp_reset.get_data(as_text=True)
