import pytest

from app import create_app
from app.database import db
from app.models.cliente import Cliente
from app.seed import seed_database
from app.services.cliente_service import ClienteService
from app.validators.cnpj_validator import CnpjValidator, limpar_documento, validar_cnpj


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


def test_cnpj_validator_normaliza_e_valida_dados_obrigatorios():
    """Teste unitário direto da classe CnpjValidator extraída na etapa REFACTOR."""
    assert CnpjValidator.normalizar_documento("18.420.331/0001-06") == "18420331000106"
    assert limpar_documento("18.420.331/0001-06") == "18420331000106"
    assert validar_cnpj("18.420.331/0001-06") is True
    assert validar_cnpj("11.111.111/1111-11") is False

    # Formatação de CPF (11 dígitos) e fallback para entrada fora do padrão
    assert CnpjValidator.formatar_documento("21843092840") == "218.430.928-40"
    assert CnpjValidator.formatar_documento("DOC-INVALIDO") == "DOC-INVALIDO"

    razao, doc_formatado = CnpjValidator.validar_dados_obrigatorios(
        {"razao_social": "  Metalúrgica Teste  ", "cpf_cnpj": "18420331000106"}
    )
    assert razao == "Metalúrgica Teste"
    assert doc_formatado == "18.420.331/0001-06"

    razao_pf, cpf_formatado = CnpjValidator.validar_dados_obrigatorios(
        {"razao_social": "Marcos Antônio Ribeiro", "cpf_cnpj": "21843092840"}
    )
    assert razao_pf == "Marcos Antônio Ribeiro"
    assert cpf_formatado == "218.430.928-40"

    with pytest.raises(ValueError, match="Formato de CPF ou CNPJ inválido"):
        CnpjValidator.validar_dados_obrigatorios(
            {"razao_social": "Metalúrgica Teste", "cpf_cnpj": "12345"}
        )


def test_rota_get_clientes_listagem_e_filtros(client):
    """Testa GET /clientes com listagem completa, busca textual e filtro por situação."""
    resp = client.get("/clientes")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "CLI-0248" in html
    assert "Construtora Horizonte Ltda." in html
    assert "Metalúrgica São Lucas" in html

    # Filtro por busca
    resp_busca = client.get("/clientes?q=Horizonte")
    assert resp_busca.status_code == 200
    html_busca = resp_busca.get_data(as_text=True)
    assert "Construtora Horizonte Ltda." in html_busca
    assert "Metalúrgica São Lucas" not in html_busca

    # Filtro por situação Inativo
    resp_inativos = client.get("/clientes?situacao=Inativo")
    assert resp_inativos.status_code == 200
    html_inativos = resp_inativos.get_data(as_text=True)
    assert "RM Projetos Industriais" in html_inativos
    assert "Construtora Horizonte Ltda." not in html_inativos


def test_rota_get_detalhe_cliente_com_historico_os(app, client):
    """Testa GET /clientes/<id> exibindo detalhes completos e as 3 O.S. da Construtora Horizonte."""
    with app.app_context():
        horizonte = Cliente.query.filter_by(codigo="CLI-0248").first()
        assert horizonte is not None
        horizonte_id = horizonte.id

    resp = client.get(f"/clientes/{horizonte_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Construtora Horizonte Ltda." in html
    assert "Horizonte Engenharia e Construções" in html
    assert "3 ordens vinculadas" in html
    assert "#OS-1048" in html
    assert "#OS-0984" in html
    assert "#OS-0912" in html


def test_rota_post_novo_cliente_sucesso(client):
    """Testa GET e POST /clientes/novo com dados válidos."""
    resp_get = client.get("/clientes/novo")
    assert resp_get.status_code == 200

    resp_post = client.post(
        "/clientes/novo",
        data={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Caldeiraria Ituana Ltda.",
            "nome_fantasia": "Ituana Industrial",
            "cpf_cnpj": "71.920.443/0001-19",
            "situacao": "Ativo",
            "telefone": "(11) 4022-8899",
            "email": "contato@ituanaindustrial.com.br",
            "cidade": "Itu",
            "estado": "SP",
        },
        follow_redirects=True,
    )
    assert resp_post.status_code == 200
    html = resp_post.get_data(as_text=True)
    assert "CLI-0249" in html
    assert "Caldeiraria Ituana Ltda." in html
    assert "cadastrado com sucesso" in html


def test_rota_post_novo_cliente_cnpj_duplicado(client):
    """Testa POST /clientes/novo bloqueando CNPJ duplicado e preservando formulário."""
    resp = client.post(
        "/clientes/novo",
        data={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Tentativa Duplicada Ltda.",
            "cpf_cnpj": "18.420.331/0001-06",
            "email": "duplicado@teste.com.br",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Este CNPJ já está cadastrado no sistema" in html
    assert "Tentativa Duplicada Ltda." in html


def test_rota_edicao_exclusao_e_cadastro_rapido_json(app, client):
    """Testa edição, inativação ao excluir cliente com O.S. e endpoint JSON de cadastro rápido."""
    # Cadastro rápido via API JSON
    resp_json = client.post(
        "/clientes/cadastro-rapido",
        json={
            "razao_social": "Serralheria Rápida Ltda.",
            "cpf_cnpj": "85.114.229/0001-62",
            "telefone": "(15) 98811-2233",
            "email": "rapida@serralheria.com.br",
        },
    )
    assert resp_json.status_code == 201
    payload = resp_json.get_json()
    assert payload["sucesso"] is True
    assert payload["cliente"]["codigo"] == "CLI-0249"
    novo_id = payload["cliente"]["id"]

    # Edição do cliente recém-criado
    resp_edit = client.post(
        f"/clientes/{novo_id}/editar",
        data={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Serralheria Rápida Sorocaba Ltda.",
            "cpf_cnpj": "85.114.229/0001-62",
            "situacao": "Ativo",
        },
        follow_redirects=True,
    )
    assert resp_edit.status_code == 200
    assert "Serralheria Rápida Sorocaba Ltda." in resp_edit.get_data(as_text=True)

    # Exclusão definitiva de cliente sem O.S.
    resp_del = client.post(f"/clientes/{novo_id}/excluir", follow_redirects=True)
    assert resp_del.status_code == 200
    assert "Cliente excluído com sucesso" in resp_del.get_data(as_text=True)

    # Tentativa de exclusão de cliente com O.S. vinculada (CLI-0248) -> deve inativar
    with app.app_context():
        horizonte = Cliente.query.filter_by(codigo="CLI-0248").first()
        horizonte_id = horizonte.id

    resp_inativar = client.post(f"/clientes/{horizonte_id}/excluir", follow_redirects=True)
    assert resp_inativar.status_code == 200
    assert "foi inativado" in resp_inativar.get_data(as_text=True)
