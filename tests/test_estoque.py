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


@pytest.fixture()
def client(app):
    return app.test_client()


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
        descricao='Disco de Corte 7"',
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


def test_rota_get_estoque_listagem_e_filtros(client):
    """Testa GET /estoque com KPIs, busca por código/descrição e filtro de categoria."""
    resp = client.get("/estoque")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "MAT-0092" in html
    assert "Chapa aço carbono 3mm" in html
    assert "Eletrodo E7018 3,25mm" in html

    # Filtro por categoria Chapas (verifica códigos na tabela Posição de estoque)
    resp_cat = client.get("/estoque?categoria=Chapas")
    assert resp_cat.status_code == 200
    html_cat = resp_cat.get_data(as_text=True)
    assert "MAT-0092" in html_cat
    assert "MAT-0089" not in html_cat
    assert "MAT-0090" not in html_cat

    # Busca textual por código MAT-0089
    resp_busca = client.get("/estoque?q=MAT-0089")
    assert resp_busca.status_code == 200
    html_busca = resp_busca.get_data(as_text=True)
    assert "MAT-0089" in html_busca
    assert "MAT-0092" not in html_busca


def test_rota_get_detalhe_material(app, client):
    """Testa GET /estoque/<id> verificando banner, recomendação de reposição e histórico."""
    with app.app_context():
        chapa = Material.query.filter_by(codigo="MAT-0092").first()
        assert chapa is not None
        chapa_id = chapa.id

    resp = client.get(f"/estoque/{chapa_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Chapa aço carbono 3mm" in html
    assert "Comprar ao menos 12 unidades" in html
    assert "Saída para OS-1048" in html
    assert "Entrada de compra" in html


def test_rota_post_novo_e_edicao_material(app, client):
    """Testa GET e POST /estoque/novo com código MAT-0093 e posterior edição."""
    resp_get = client.get("/estoque/novo")
    assert resp_get.status_code == 200
    assert "MAT-0093" in resp_get.get_data(as_text=True)

    resp_post = client.post(
        "/estoque/novo",
        data={
            "codigo": "MAT-0093",
            "descricao": "Perfil U Enrijecido 100×40",
            "categoria": "Perfis",
            "tipo_material": "Aço estrutural",
            "unidade": "BR",
            "quantidade_inicial": "0",
            "minimo": "10",
            "custo_unitario": "145,00",
            "fornecedor": "Gerdau Aços",
            "localizacao": "Setor B · Rack 06",
            "situacao": "Ativo",
        },
        follow_redirects=True,
    )
    assert resp_post.status_code == 200
    html_lista = resp_post.get_data(as_text=True)
    assert "MAT-0093" in html_lista
    assert "Perfil U Enrijecido 100×40" in html_lista
    assert "Indisponível" in html_lista

    with app.app_context():
        criado = Material.query.filter_by(codigo="MAT-0093").first()
        assert criado is not None
        criado_id = criado.id

    resp_edit = client.post(
        f"/estoque/{criado_id}/editar",
        data={
            "codigo": "MAT-0093",
            "descricao": "Perfil U Enrijecido 100×40×2,65mm",
            "categoria": "Perfis",
            "tipo_material": "Aço estrutural",
            "unidade": "BR",
            "disponivel": "15",
            "minimo": "10",
            "custo_unitario": "149,90",
        },
        follow_redirects=True,
    )
    assert resp_edit.status_code == 200
    assert "Perfil U Enrijecido 100×40×2,65mm" in resp_edit.get_data(as_text=True)


def test_rota_post_movimentar_entrada_e_bloqueio_saida_insuficiente(app, client):
    """Testa POST /estoque/<id>/movimentar com entrada válida e com bloqueio RN02 de saldo insuficiente."""
    with app.app_context():
        chapa = Material.query.filter_by(codigo="MAT-0092").first()
        assert chapa is not None
        assert chapa.disponivel == 8.0
        chapa_id = chapa.id

    # 1. Entrada válida (+ 5 un. -> saldo passa para 13)
    resp_entrada = client.post(
        f"/estoque/{chapa_id}/movimentar",
        data={
            "tipo": "Entrada",
            "quantidade": "5",
            "responsavel": "Mariana Alves",
            "descricao_movimentacao": "Reposição parcial NF-4410",
        },
        follow_redirects=True,
    )
    assert resp_entrada.status_code == 200
    html_entrada = resp_entrada.get_data(as_text=True)
    assert "Entrada de estoque registrada com sucesso" in html_entrada
    assert "Reposição parcial NF-4410" in html_entrada

    with app.app_context():
        assert db.session.get(Material, chapa_id).disponivel == 13.0

    # 2. Saída maior que o saldo disponível (tentar retirar 25 un. tendo apenas 13 -> bloqueia RN02)
    resp_saida_erro = client.post(
        f"/estoque/{chapa_id}/movimentar",
        data={
            "tipo": "Saída",
            "quantidade": "25",
            "responsavel": "Carlos Mendes",
            "descricao_movimentacao": "Tentativa acima do saldo",
        },
        follow_redirects=True,
    )
    assert resp_saida_erro.status_code == 200
    html_erro = resp_saida_erro.get_data(as_text=True)
    assert "Saldo insuficiente no estoque" in html_erro

    with app.app_context():
        assert db.session.get(Material, chapa_id).disponivel == 13.0


def test_validacoes_unitarias_estoque_service(app):
    """Cobre validações numéricas, resolução por ID e regras de unicidade/obrigatoriedade em EstoqueService."""
    with app.app_context():
        service = EstoqueService()
        assert service.repository is service.repositorio

        chapa = Material.query.filter_by(codigo="MAT-0092").first()
        assert chapa is not None

        # Resolução por ID inteiro e bloqueio para ID inexistente
        atualizado = service.registrar_entrada(chapa.id, "R$ 1.002,50")
        assert atualizado.disponivel == 1010.5
        with pytest.raises(ValueError, match="Material não encontrado"):
            service.registrar_entrada(99999, 5)

        # Validações de conversão numérica (vazio obrigatório, texto inválido, zero e negativo)
        with pytest.raises(ValueError, match="Informe um valor válido"):
            service.registrar_entrada(chapa, "")
        with pytest.raises(ValueError, match="Valor numérico inválido"):
            service.registrar_entrada(chapa, "abc")
        with pytest.raises(ValueError, match="deve ser maior que zero"):
            service.registrar_entrada(chapa, 0)
        with pytest.raises(ValueError, match="não pode ser negativo"):
            service.cadastrar_material({"descricao": "Item Negativo", "minimo": -2})

        # Validações de cadastro e atualização (descrição vazia, código duplicado e subtítulo)
        with pytest.raises(ValueError, match="Nome ou Descrição do material é obrigatório"):
            service.cadastrar_material({"descricao": "   "})
        with pytest.raises(ValueError, match="já está cadastrado no estoque"):
            service.cadastrar_material({"codigo": "MAT-0092", "descricao": "Duplicado"})
        with pytest.raises(ValueError, match="Material não encontrado"):
            service.atualizar_material(99999, {"descricao": "Inexistente"})
        with pytest.raises(ValueError, match="Nome ou Descrição do material é obrigatório"):
            service.atualizar_material(chapa.id, {"descricao": ""})
        with pytest.raises(ValueError, match="já está cadastrado no estoque"):
            service.atualizar_material(
                chapa.id,
                {"descricao": "Chapa aço carbono 3mm", "codigo": "MAT-0091"},
            )

        editado = service.atualizar_material(
            chapa.id,
            {
                "descricao": "Chapa aço carbono 3mm",
                "subtitulo": "Chapa laminada a quente certificada",
                "minimo": "",
            },
        )
        assert editado.subtitulo == "Chapa laminada a quente certificada"


def test_cadastro_material_com_categoria_tipo_e_unidade_personalizados(app, client):
    """ETAPA 6 (PASSO 4 / PASSO 7): Valida cadastro de material com categoria, tipo e unidade 100% customizados e filtro dinâmico."""
    resp_post = client.post(
        "/estoque/novo",
        data={
            "codigo": "MAT-0093",
            "descricao": "Parafuso Sextavado Estrutural M16",
            "categoria": "Fixadores Especiais",
            "tipo_material": "Aço Liga Temperado 8.8",
            "unidade": "CENTO",
            "quantidade_inicial": "12",
            "minimo": "5",
            "custo_unitario": "95,00",
            "fornecedor": "Fixadores Ribeirão",
            "localizacao": "Setor C · Gaveteiro 12",
            "situacao": "Ativo",
        },
        follow_redirects=True,
    )
    assert resp_post.status_code == 200
    html_lista = resp_post.get_data(as_text=True)
    assert "MAT-0093" in html_lista
    assert "Parafuso Sextavado Estrutural M16" in html_lista
    assert "Fixadores Especiais" in html_lista
    assert "CENTO" in html_lista

    # Verifica que o filtro dinâmico por categoria personalizada funciona na rota GET /estoque
    resp_filtro = client.get("/estoque?categoria=Fixadores+Especiais")
    assert resp_filtro.status_code == 200
    html_filtro = resp_filtro.get_data(as_text=True)
    assert "MAT-0093" in html_filtro
    assert "MAT-0092" not in html_filtro
