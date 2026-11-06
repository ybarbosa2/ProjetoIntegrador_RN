import pytest

from app import create_app
from app.database import db
from app.models.cliente import Cliente
from app.seed import seed_database
from app.services.cliente_service import ClienteService
from app.validators.cnpj_validator import (
    CnpjValidator,
    limpar_documento,
    validar_cnpj,
    validar_cpf,
)


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
            "cpf_cnpj": "18.420.331/0001-46",  # CNPJ já pertencente ao CLI-0248
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
            "cpf_cnpj": "63.812.509/0001-59",
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
        assert persistido.cpf_cnpj == "63.812.509/0001-59"


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
    assert CnpjValidator.normalizar_documento("18.420.331/0001-46") == "18420331000146"
    assert limpar_documento("18.420.331/0001-46") == "18420331000146"
    assert validar_cnpj("18.420.331/0001-46") is True
    assert validar_cnpj("11.111.111/1111-11") is False
    assert validar_cpf("218.430.928-16") is True
    assert validar_cpf("111.111.111-11") is False

    # Formatação de CPF (11 dígitos) e fallback para entrada fora do padrão
    assert CnpjValidator.formatar_documento("21843092816") == "218.430.928-16"
    assert CnpjValidator.formatar_documento("DOC-INVALIDO") == "DOC-INVALIDO"

    razao, doc_formatado = CnpjValidator.validar_dados_obrigatorios(
        {"razao_social": "  Metalúrgica Teste  ", "cpf_cnpj": "18420331000146"}
    )
    assert razao == "Metalúrgica Teste"
    assert doc_formatado == "18.420.331/0001-46"

    razao_pf, cpf_formatado = CnpjValidator.validar_dados_obrigatorios(
        {
            "tipo_pessoa": "Pessoa física",
            "razao_social": "Marcos Antônio Ribeiro",
            "cpf_cnpj": "21843092816",
        }
    )
    assert razao_pf == "Marcos Antônio Ribeiro"
    assert cpf_formatado == "218.430.928-16"

    with pytest.raises(ValueError, match="CNPJ inválido para Pessoa Jurídica"):
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
            "cpf_cnpj": "71.920.443/0001-49",
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
            "cpf_cnpj": "18.420.331/0001-46",
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
            "cpf_cnpj": "85.114.229/0001-00",
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
            "cpf_cnpj": "85.114.229/0001-00",
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


def test_deve_rejeitar_cpf_em_cadastro_pessoa_juridica(app, client, cliente_service):
    """QA Bug 4a: Deve rejeitar CPF (11 dígitos) em cadastro de Pessoa Jurídica e CNPJ em Pessoa Física."""
    with app.app_context():
        # CPF matematicamente válido porém enviado para Pessoa Jurídica
        with pytest.raises(
            ValueError,
            match="CNPJ inválido para Pessoa Jurídica. Informe um CNPJ real com 14 dígitos.",
        ):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa jurídica",
                    "razao_social": "Empresa Com CPF Ltda.",
                    "cpf_cnpj": "218.430.928-16",
                }
            )

        # CNPJ matematicamente válido porém enviado para Pessoa Física
        with pytest.raises(
            ValueError,
            match="CPF inválido para Pessoa Física. Informe um CPF real com 11 dígitos.",
        ):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa física",
                    "razao_social": "João da Silva",
                    "cpf_cnpj": "12.345.678/0001-95",
                }
            )

    resp_rapido = client.post(
        "/clientes/cadastro-rapido",
        json={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Empresa Com CPF no Modal Ltda.",
            "cpf_cnpj": "218.430.928-16",
        },
    )
    assert resp_rapido.status_code == 400
    assert "CNPJ inválido para Pessoa Jurídica" in resp_rapido.get_json()["erro"]


def test_deve_rejeitar_cnpj_ou_cpf_com_digito_verificador_invalido(app, cliente_service):
    """QA Bug 4b: Deve rejeitar CPF e CNPJ com dígitos verificadores matematicamente inválidos ou repetidos."""
    with app.app_context():
        # CNPJ com dígito verificador incorreto (-06 em vez de -46)
        with pytest.raises(ValueError, match="CNPJ inválido para Pessoa Jurídica"):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa jurídica",
                    "razao_social": "Metalúrgica DV Inválido Ltda.",
                    "cpf_cnpj": "18.420.331/0001-06",
                }
            )

        # CNPJ com todos os dígitos repetidos
        with pytest.raises(ValueError, match="CNPJ inválido para Pessoa Jurídica"):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa jurídica",
                    "razao_social": "Metalúrgica Zeros Ltda.",
                    "cpf_cnpj": "00.000.000/0000-00",
                }
            )

        # CPF com dígito verificador incorreto (-40 em vez de -16)
        with pytest.raises(ValueError, match="CPF inválido para Pessoa Física"):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa física",
                    "razao_social": "Cliente PF DV Inválido",
                    "cpf_cnpj": "218.430.928-40",
                }
            )

        # CPF com todos os dígitos repetidos
        with pytest.raises(ValueError, match="CPF inválido para Pessoa Física"):
            cliente_service.cadastrar_cliente(
                {
                    "tipo_pessoa": "Pessoa física",
                    "razao_social": "Cliente PF Repetido",
                    "cpf_cnpj": "111.111.111-11",
                }
            )


def test_deve_rejeitar_telefone_e_email_invalidos_no_cadastro_rapido(client):
    """QA Bug 5: Deve rejeitar telefone '11' e e-mail 'as' tanto no cadastro rápido quanto no completo."""
    # Telefone curto inválido ("11")
    resp_tel = client.post(
        "/clientes/cadastro-rapido",
        json={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Cliente Telefone Curto Ltda.",
            "cpf_cnpj": "12.345.678/0001-95",
            "telefone": "11",
            "email": "contato@empresa.com.br",
        },
    )
    assert resp_tel.status_code == 400
    dados_tel = resp_tel.get_json()
    assert dados_tel["sucesso"] is False
    assert "Telefone inválido. Informe o DDD e o número completo (10 ou 11 dígitos)." in dados_tel["erro"]

    # E-mail inválido ("as")
    resp_email = client.post(
        "/clientes/cadastro-rapido",
        json={
            "tipo_pessoa": "Pessoa jurídica",
            "razao_social": "Cliente Email Invalido Ltda.",
            "cpf_cnpj": "12.345.678/0001-95",
            "telefone": "(16) 99742-1280",
            "email": "as",
        },
    )
    assert resp_email.status_code == 400
    dados_email = resp_email.get_json()
    assert dados_email["sucesso"] is False
    assert "E-mail inválido. Informe um endereço completo" in dados_email["erro"]


def test_paginacao_real_e_dinamica_clientes(app, client):
    """QA Bug 3: Verifica indicador Página 1 de 1 com poucos registros e paginação real acima de 10."""
    resp_p1_unica = client.get("/clientes")
    html_unica = resp_p1_unica.get_data(as_text=True)
    assert "Página 1 de 1" in html_unica
    assert "?page=2" not in html_unica
    assert "Mais filtros" not in html_unica

    # Insere mais 6 clientes válidos para totalizar 12 (> 10 por página)
    with app.app_context():
        for idx in range(6):
            db.session.add(
                Cliente(
                    codigo=f"CLI-090{idx}",
                    tipo_pessoa="Pessoa jurídica",
                    razao_social=f"Cliente Paginação {idx} Ltda.",
                    cpf_cnpj=f"99.000.00{idx}/0001-00",
                    situacao="Ativo",
                )
            )
        db.session.commit()

    resp_p1 = client.get("/clientes?page=1")
    html_p1 = resp_p1.get_data(as_text=True)
    assert "Exibindo 1–10 de 12 registros" in html_p1
    assert "page=2" in html_p1

    resp_p2 = client.get("/clientes?page=2")
    html_p2 = resp_p2.get_data(as_text=True)
    assert "Exibindo 11–12 de 12 registros" in html_p2
