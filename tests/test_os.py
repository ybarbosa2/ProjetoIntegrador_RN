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
def client(app):
    return app.test_client()


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


def test_rota_get_os_listagem_e_filtros(client):
    """Testa GET /os com listagem completa, busca textual e filtro por status."""
    resp = client.get("/os")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "#OS-1048" in html
    assert "#OS-1047" in html
    assert "Construtora Horizonte Ltda." in html

    # Filtro por status Aguardando material
    resp_status = client.get("/os?status=Aguardando+material")
    assert resp_status.status_code == 200
    html_status = resp_status.get_data(as_text=True)
    assert "#OS-1047" in html_status
    assert "#OS-1048" not in html_status

    # Busca por número
    resp_busca = client.get("/os?q=OS-1046")
    assert resp_busca.status_code == 200
    html_busca = resp_busca.get_data(as_text=True)
    assert "#OS-1046" in html_busca
    assert "#OS-1048" not in html_busca


def test_rota_get_detalhe_os_e_modal_orcamento(app, client):
    """Testa GET /os/<id> exibindo resumo financeiro R$ 11.247,40, materiais e proposta ORC-1048."""
    with app.app_context():
        os_1048 = OrdemServico.query.filter_by(numero="OS-1048").first()
        assert os_1048 is not None
        os_id = os_1048.id

    resp = client.get(f"/os/{os_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Ordem de Serviço #OS-1048" in html
    assert "R$ 8.500,00" in html
    assert "R$ 2.747,40" in html
    assert "R$ 11.247,40" in html
    assert "PROPOSTA ORC-1048" in html
    assert "Chapa aço carbono 3mm" in html


def test_rota_post_nova_os_sucesso_e_edicao(app, client):
    """Testa GET/POST /os/nova vinculando cliente e materiais do estoque com baixa automática."""
    resp_get = client.get("/os/nova")
    assert resp_get.status_code == 200
    assert "OS-1049" in resp_get.get_data(as_text=True)
    assert "Cadastro Rápido de Cliente" in resp_get.get_data(as_text=True)

    with app.app_context():
        cliente = Cliente.query.filter_by(codigo="CLI-0247").first()
        material = Material.query.filter_by(codigo="MAT-0088").first()  # Saldo inicial: 38
        cliente_id = cliente.id
        material_id = material.id

    resp_post = client.post(
        "/os/nova",
        data={
            "numero": "OS-1049",
            "cliente_id": str(cliente_id),
            "data_abertura": "14/06/2025",
            "prazo_entrega": "30/06/2025",
            "status": "Em andamento",
            "tipo_servico": "Manutenção industrial",
            "titulo_resumo": "Adequação de plataforma metálica",
            "quantidade_servico": "1 conjunto",
            "responsavel": "Bruno Lima",
            "descricao_detalhada": "Reforço estrutural com barras chatas de aço carbono.",
            "valor_mao_de_obra": "3500,00",
            "material_id[]": [str(material_id)],
            "material_quantidade[]": ["4"],
        },
        follow_redirects=True,
    )
    assert resp_post.status_code == 200
    html_detalhe = resp_post.get_data(as_text=True)
    assert "Ordem de Serviço #OS-1049" in html_detalhe
    assert "PROPOSTA ORC-1049" in html_detalhe
    assert "R$ 3.846,00" in html_detalhe  # 3500 + (4 * 86.50 = 346)

    with app.app_context():
        assert db.session.get(Material, material_id).disponivel == 34.0
        criada = OrdemServico.query.filter_by(numero="OS-1049").first()
        criada_id = criada.id

    # Atualização rápida de status via POST /os/<id>/editar
    resp_edit = client.post(
        f"/os/{criada_id}/editar",
        data={"status": "Concluída"},
        follow_redirects=True,
    )
    assert resp_edit.status_code == 200
    assert "Concluída" in resp_edit.get_data(as_text=True)


def test_rota_post_nova_os_sem_cliente_exibe_erro(client):
    """Testa POST /os/nova sem cliente selecionado retornando mensagem de erro RN03."""
    resp = client.post(
        "/os/nova",
        data={
            "numero": "OS-1049",
            "cliente_id": "",
            "tipo_servico": "Serralheria industrial",
            "descricao_detalhada": "Tentativa sem cliente",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Cliente obrigatório não selecionado" in html


def test_fluxo_cadastro_rapido_cliente_e_abertura_os(client):
    """Testa integração entre POST /clientes/cadastro-rapido (UC01-A1) e POST /os/nova."""
    resp_rapido = client.post(
        "/clientes/cadastro-rapido",
        json={
            "razao_social": "Metalúrgica Votorantim Express Ltda.",
            "cpf_cnpj": "91.334.552/0001-08",
            "telefone": "(15) 3243-9900",
            "email": "contato@votorantimexpress.com.br",
        },
    )
    assert resp_rapido.status_code == 201
    dados_json = resp_rapido.get_json()
    assert dados_json["sucesso"] is True
    novo_cliente_id = dados_json["cliente"]["id"]

    resp_os = client.post(
        "/os/nova",
        data={
            "cliente_id": str(novo_cliente_id),
            "tipo_servico": "Fabricação de estrutura metálica",
            "titulo_resumo": "Cobertura metálica doca 02",
            "descricao_detalhada": "Cobertura metálica industrial.",
            "valor_mao_de_obra": "6200,00",
        },
        follow_redirects=True,
    )
    assert resp_os.status_code == 200
    html = resp_os.get_data(as_text=True)
    assert "Metalúrgica Votorantim Express Ltda." in html
    assert "Ordem de Serviço #OS-1049" in html


def test_validacoes_unitarias_os_service(app, os_service):
    """Cobre regras de exceção, validações monetárias, vínculo de estoque e atualização completa em OsService."""
    with app.app_context():
        assert os_service.repository is os_service.os_repository

        cliente_horizonte = Cliente.query.filter_by(codigo="CLI-0248").first()
        cliente_nova_era = Cliente.query.filter_by(codigo="CLI-0247").first()
        chapa = Material.query.filter_by(codigo="MAT-0092").first()  # Saldo inicial: 8
        os_1048 = OrdemServico.query.filter_by(numero="OS-1048").first()

        # Orçamento por ID inteiro e erro para O.S. inexistente
        orc = os_service.gerar_orcamento(os_1048.id)
        assert orc["codigo_orcamento"] == "ORC-1048"
        with pytest.raises(ValueError, match="Ordem de Serviço não encontrada"):
            os_service.gerar_orcamento(99999)

        # Validações de cliente inválido ou inexistente (RN03)
        with pytest.raises(ValueError, match="Cliente obrigatório não selecionado"):
            os_service.criar_ordem_servico({"cliente_id": "invalido", "tipo_servico": "Solda"})
        with pytest.raises(ValueError, match="Cliente obrigatório não selecionado"):
            os_service.criar_ordem_servico({"cliente_id": 99999, "tipo_servico": "Solda"})

        # O.S. sem descrição/tipo e número duplicado
        with pytest.raises(ValueError, match="Informe o tipo ou a descrição"):
            os_service.criar_ordem_servico(
                {
                    "cliente_id": cliente_horizonte.id,
                    "tipo_servico": "",
                    "descricao_detalhada": "",
                    "titulo_resumo": "",
                }
            )
        with pytest.raises(ValueError, match="já está em uso"):
            os_service.criar_ordem_servico(
                {
                    "cliente_id": cliente_horizonte.id,
                    "numero": "OS-1048",
                    "tipo_servico": "Solda industrial",
                }
            )

        # Validações de valor monetário inválido / negativo
        with pytest.raises(ValueError, match="Valor inválido"):
            os_service.criar_ordem_servico(
                {
                    "cliente_id": cliente_horizonte.id,
                    "tipo_servico": "Solda",
                    "valor_mao_de_obra": "abc",
                }
            )
        with pytest.raises(ValueError, match="não pode ser negativo"):
            os_service.criar_ordem_servico(
                {
                    "cliente_id": cliente_horizonte.id,
                    "tipo_servico": "Solda",
                    "valor_mao_de_obra": -100,
                }
            )

        # Validações de materiais na criação da O.S. (inexistente e saldo insuficiente RN02)
        with pytest.raises(ValueError, match="não encontrado no estoque"):
            os_service.criar_ordem_servico(
                {"cliente_id": cliente_horizonte.id, "tipo_servico": "Solda"},
                lista_materiais=[{"material_id": 99999, "quantidade": 1}],
            )
        with pytest.raises(ValueError, match="Saldo insuficiente no estoque"):
            os_service.criar_ordem_servico(
                {"cliente_id": cliente_horizonte.id, "tipo_servico": "Solda"},
                lista_materiais=[{"material_id": chapa.id, "quantidade": 50}],
            )

        # Criação com resumo automático, formato monetário R$ 1.250,50 e linhas vazias ignoradas
        criada = os_service.criar_ordem_servico(
            {
                "cliente_id": cliente_horizonte.id,
                "tipo_servico": "Caldeiraria pesada",
                "descricao_detalhada": "Fabricação de tremonha industrial em aço carbono.",
                "valor_mao_de_obra": "R$ 1.250,50",
            },
            lista_materiais=[
                {"material_id": "", "quantidade": "2"},
                {"material_id": chapa.id, "quantidade": "0"},
                {"material_id": chapa.id, "quantidade": ""},
            ],
        )
        assert criada.titulo_resumo == "Fabricação de tremonha industrial em aço carbono."
        assert criada.valor_mao_de_obra == 1250.50

        # Atualização completa de dados e validações de exceção
        with pytest.raises(ValueError, match="Ordem de Serviço não encontrada"):
            os_service.atualizar_status_ou_dados(99999, {"status": "Concluída"})
        with pytest.raises(ValueError, match="Cliente obrigatório não selecionado"):
            os_service.atualizar_status_ou_dados(criada.id, {"cliente_id": 99999})

        atualizada = os_service.atualizar_status_ou_dados(
            criada.id,
            {
                "cliente_id": cliente_nova_era.id,
                "status": "Em andamento",
                "data_abertura": "15/06/2025",
                "prazo_entrega": "29/06/2025",
                "titulo_resumo": "Tremonha industrial reforçada",
                "tipo_servico": "Caldeiraria e solda",
                "quantidade_servico": "2 conjuntos",
                "responsavel": "André Souza",
                "descricao_detalhada": "Tremonha com reforço estrutural lateral.",
                "especificacoes_tecnicas": "Solda MIG contínua e primer anticorrosivo.",
                "valor_mao_de_obra": "R$ 2.100,00",
            },
        )
        assert atualizada.cliente_id == cliente_nova_era.id
        assert atualizada.titulo_resumo == "Tremonha industrial reforçada"
        assert atualizada.valor_mao_de_obra == 2100.00


def test_criar_os_com_prazo_entrega_vazio_opcional(app, client, os_service):
    """ETAPA 6 (PASSO 5.2 / PASSO 7): Valida criação de O.S. com prazo_entrega vazio (não obrigatório)."""
    with app.app_context():
        cliente = Cliente.query.filter_by(codigo="CLI-0248").first()
        nova_os = os_service.criar_ordem_servico(
            {
                "cliente_id": cliente.id,
                "prazo_entrega": "",
                "tipo_servico": "Manutenção industrial",
                "descricao_detalhada": "Manutenção corretiva sem prazo pré-fixado.",
                "valor_mao_de_obra": "1800,00",
            }
        )
        assert nova_os.id is not None
        assert nova_os.prazo_entrega == ""
        os_id = nova_os.id

    resp_detalhe = client.get(f"/os/{os_id}")
    assert resp_detalhe.status_code == 200
    assert "A definir" in resp_detalhe.get_data(as_text=True)


def test_edicao_os_completa_com_sincronizacao_inteligente_estoque(app, client):
    """ETAPA 6 (PASSO 5.3 / PASSO 7): Edita descrição, mão de obra, adiciona novo material e remove material existente."""
    with app.app_context():
        # OS-1048 possui inicialmente:
        # - MAT-0092 (6 un. a R$ 284,90; saldo atual no estoque = 8.0)
        # - MAT-0088 (12 br. a R$ 86,50; saldo atual no estoque = 38.0)
        # E MAT-0090 possui saldo atual no estoque = 46.0 e custo_unitario = R$ 110,00
        os_1048 = OrdemServico.query.filter_by(numero="OS-1048").first()
        mat_chapa = Material.query.filter_by(codigo="MAT-0092").first()
        mat_barra = Material.query.filter_by(codigo="MAT-0088").first()
        mat_cantoneira = Material.query.filter_by(codigo="MAT-0090").first()

        os_id = os_1048.id
        chapa_id = mat_chapa.id
        barra_id = mat_barra.id
        cantoneira_id = mat_cantoneira.id

    # Na edição da OS-1048:
    # 1. Mantém MAT-0092 aumentando de 6 para 8 un. (baixa +2 do estoque -> saldo de MAT-0092 cai de 8 para 6)
    # 2. Remove MAT-0088 (estorna 12 br. ao estoque -> saldo de MAT-0088 sobe de 38 para 50)
    # 3. Adiciona MAT-0090 com 4 br. (baixa 4 do estoque -> saldo de MAT-0090 cai de 46 para 42)
    # 4. Altera descrição detalhada e valor da mão de obra para R$ 9.000,00
    resp_edit = client.post(
        f"/os/{os_id}/editar",
        data={
            "sincronizar_materiais": "1",
            "status": "Em andamento",
            "tipo_servico": "Fabricação de estrutura metálica",
            "titulo_resumo": "Estrutura metálica galpão principal",
            "descricao_detalhada": "Fabricação, reforço de tesouras e montagem completa do galpão.",
            "especificacoes_tecnicas": "Solda MIG certificada e pintura epóxi.",
            "valor_mao_de_obra": "9000,00",
            "material_id[]": [str(chapa_id), str(cantoneira_id)],
            "material_quantidade[]": ["8", "4"],
        },
        follow_redirects=True,
    )
    assert resp_edit.status_code == 200
    html = resp_edit.get_data(as_text=True)
    assert "Fabricação, reforço de tesouras e montagem completa do galpão." in html
    assert "R$ 9.000,00" in html

    with app.app_context():
        os_atualizada = db.session.get(OrdemServico, os_id)
        # Materiais: (8 * 284,90 = 2.279,20) + (4 * 110,00 = 440,00) = 2.719,20
        assert round(os_atualizada.valor_materiais, 2) == 2719.20
        assert round(os_atualizada.valor_mao_de_obra, 2) == 9000.00
        assert round(os_atualizada.valor_total, 2) == 11719.20

        # Verifica saldos atualizados no estoque
        assert db.session.get(Material, chapa_id).disponivel == 6.0  # 8 - 2
        assert db.session.get(Material, barra_id).disponivel == 50.0  # 38 + 12 (estornado)
        assert db.session.get(Material, cantoneira_id).disponivel == 42.0  # 46 - 4 (baixado)
