from app.database import db
from app.models.cliente import Cliente
from app.models.material import Material, MovimentacaoEstoque
from app.models.ordem_servico import ItemOrdemServico, OrdemServico


def seed_database() -> None:
    """Popula o banco de dados com o seed fiel ao protótipo do Figma se a tabela Cliente estiver vazia."""
    if Cliente.query.first() is not None:
        return

    # 1. Clientes (CNPJs e CPF com dígitos verificadores reais da Receita Federal)
    cli_0248 = Cliente(
        codigo="CLI-0248",
        tipo_pessoa="Pessoa jurídica",
        razao_social="Construtora Horizonte Ltda.",
        nome_fantasia="Horizonte Engenharia e Construções",
        cpf_cnpj="18.420.331/0001-46",
        inscricao_estadual="669.842.110.117",
        telefone="(15) 3312-8400",
        email="compras@horizonte.com.br",
        cep="18013-280",
        endereco="Av. Eng. Carlos Reinaldo Mendes",
        numero="1840",
        bairro="Alto da Boa Vista",
        cidade="Sorocaba",
        estado="SP",
        situacao="Ativo",
        observacoes=(
            "Cliente com atendimento prioritário. Solicitações devem ser direcionadas "
            "ao setor de suprimentos. Condição comercial negociada para 28 dias."
        ),
    )

    cli_0247 = Cliente(
        codigo="CLI-0247",
        tipo_pessoa="Pessoa jurídica",
        razao_social="Indústria Nova Era S.A.",
        nome_fantasia="Nova Era Industrial",
        cpf_cnpj="42.580.176/0001-00",
        inscricao_estadual="114.920.331.110",
        telefone="(11) 4082-1290",
        email="suprimentos@novaera.com.br",
        cidade="São Paulo",
        estado="SP",
        situacao="Ativo",
    )

    cli_0246 = Cliente(
        codigo="CLI-0246",
        tipo_pessoa="Pessoa física",
        razao_social="Marcos Antônio Ribeiro",
        cpf_cnpj="218.430.928-16",
        telefone="(15) 99742-1280",
        email="marcos.ribeiro@email.com",
        cidade="Sorocaba",
        estado="SP",
        situacao="Ativo",
    )

    cli_0245 = Cliente(
        codigo="CLI-0245",
        tipo_pessoa="Pessoa jurídica",
        razao_social="Grupo Aliança Engenharia",
        nome_fantasia="Aliança Engenharia",
        cpf_cnpj="07.442.991/0001-01",
        telefone="(15) 3035-4770",
        email="contato@aliancaeng.com.br",
        cidade="Sorocaba",
        estado="SP",
        situacao="Ativo",
    )

    cli_0244 = Cliente(
        codigo="CLI-0244",
        tipo_pessoa="Pessoa jurídica",
        razao_social="RM Projetos Industriais",
        nome_fantasia="RM Engenharia",
        cpf_cnpj="31.987.402/0001-55",
        telefone="(11) 4198-0122",
        email="projetos@rmindustrial.com.br",
        cidade="Campinas",
        estado="SP",
        situacao="Inativo",
    )

    cli_0243 = Cliente(
        codigo="CLI-0243",
        tipo_pessoa="Pessoa jurídica",
        razao_social="Metalúrgica São Lucas",
        nome_fantasia="São Lucas Metalurgia",
        cpf_cnpj="54.203.114/0001-68",
        telefone="(15) 3228-9044",
        email="financeiro@saolucas.com.br",
        cidade="Sorocaba",
        estado="SP",
        situacao="Ativo",
    )

    db.session.add_all([cli_0248, cli_0247, cli_0246, cli_0245, cli_0244, cli_0243])
    db.session.flush()

    # 2. Materiais (Estoque)
    mat_0092 = Material(
        codigo="MAT-0092",
        descricao="Chapa aço carbono 3mm",
        subtitulo="Aço carbono laminado a quente",
        categoria="Chapas",
        tipo_material="Aço carbono",
        unidade="UN",
        disponivel=8.0,
        minimo=20.0,
        custo_unitario=284.90,
        fornecedor="Aços Paulista Distribuidora",
        localizacao="Setor A · Estante 04 · Nível 02",
        observacoes=(
            "Chapa padrão 1200 × 3000mm. Armazenar em local coberto e seco, "
            "com separadores de madeira entre lotes."
        ),
    )

    mat_0091 = Material(
        codigo="MAT-0091",
        descricao="Tubo retangular 40×20×1,5mm",
        categoria="Tubos",
        tipo_material="Aço carbono",
        unidade="M",
        disponivel=12.0,
        minimo=30.0,
        custo_unitario=65.00,
        fornecedor="Aços Paulista Distribuidora",
        localizacao="Setor B · Rack 02",
    )

    mat_0090 = Material(
        codigo="MAT-0090",
        descricao='Cantoneira 1.1/2" × 3/16"',
        categoria="Perfis",
        tipo_material="Aço estrutural",
        unidade="BR",
        disponivel=46.0,
        minimo=15.0,
        custo_unitario=110.00,
        fornecedor="Gerdau Aços",
        localizacao="Setor B · Rack 05",
    )

    mat_0089 = Material(
        codigo="MAT-0089",
        descricao="Eletrodo E7018 3,25mm",
        categoria="Consumíveis",
        tipo_material="Insumo de solda",
        unidade="KG",
        disponivel=4.0,
        minimo=10.0,
        custo_unitario=42.00,
        fornecedor="Esab Brasil",
        localizacao="Almoxarifado Central · Armário 01",
    )

    mat_0088 = Material(
        codigo="MAT-0088",
        descricao='Barra chata 2" × 1/4"',
        categoria="Barras",
        tipo_material="Aço carbono",
        unidade="BR",
        disponivel=38.0,
        minimo=12.0,
        custo_unitario=86.50,
        fornecedor="Aços Paulista Distribuidora",
        localizacao="Setor A · Estante 02",
    )

    db.session.add_all([mat_0092, mat_0091, mat_0090, mat_0089, mat_0088])
    db.session.flush()

    # 3. Movimentações de Estoque
    movimentacoes = [
        MovimentacaoEstoque(
            material_id=mat_0092.id,
            data_hora="13/06/2025 · 09:42",
            tipo="Saída",
            descricao_movimentacao="Saída para OS-1048",
            quantidade=6.0,
            responsavel="Carlos Mendes",
        ),
        MovimentacaoEstoque(
            material_id=mat_0092.id,
            data_hora="10/06/2025 · 14:18",
            tipo="Entrada",
            descricao_movimentacao="Entrada de compra",
            quantidade=20.0,
            responsavel="Mariana Alves",
        ),
        MovimentacaoEstoque(
            material_id=mat_0091.id,
            data_hora="13/06/2025 · 08:15",
            tipo="Saída",
            descricao_movimentacao="Saída para OS-1047",
            quantidade=18.0,
            responsavel="Bruno Lima",
        ),
        MovimentacaoEstoque(
            material_id=mat_0089.id,
            data_hora="12/06/2025 · 16:20",
            tipo="Saída",
            descricao_movimentacao="Consumo interno oficina",
            quantidade=6.0,
            responsavel="André Souza",
        ),
        MovimentacaoEstoque(
            material_id=mat_0088.id,
            data_hora="12/06/2025 · 14:08",
            tipo="Entrada",
            descricao_movimentacao="Entrada de compra",
            quantidade=20.0,
            responsavel="Mariana Alves",
        ),
    ]
    db.session.add_all(movimentacoes)

    # 4. Ordens de Serviço
    os_1048 = OrdemServico(
        numero="OS-1048",
        cliente_id=cli_0248.id,
        titulo_resumo="Estrutura metálica galpão",
        tipo_servico="Fabricação de estrutura metálica",
        quantidade_servico="1 conjunto",
        data_abertura="13/06/2025",
        prazo_entrega="28/06/2025",
        responsavel="Carlos Mendes",
        status="Em andamento",
        valor_mao_de_obra=8500.00,
        descricao_detalhada=(
            "Fabricação e montagem de estrutura metálica para ampliação do galpão industrial."
        ),
        especificacoes_tecnicas=(
            "Perfis ASTM A36, acabamento com pintura epóxi cinza, conforme desenho RN-284-B."
        ),
        itens=[
            ItemOrdemServico(
                material_id=mat_0092.id,
                quantidade=6.0,
                valor_unitario=284.90,
            ),
            ItemOrdemServico(
                material_id=mat_0088.id,
                quantidade=12.0,
                valor_unitario=86.50,
            ),
        ],
    )

    os_1047 = OrdemServico(
        numero="OS-1047",
        cliente_id=cli_0247.id,
        titulo_resumo="Portão industrial automático",
        tipo_servico="Fabricação e automação",
        data_abertura="12/06/2025",
        prazo_entrega="22/06/2025",
        responsavel="Bruno Lima",
        status="Aguardando material",
        valor_mao_de_obra=4200.00,
    )

    os_1046 = OrdemServico(
        numero="OS-1046",
        cliente_id=cli_0245.id,
        titulo_resumo="Mezanino metálico 180m²",
        tipo_servico="Fabricação de estrutura metálica",
        data_abertura="12/06/2025",
        prazo_entrega="05/07/2025",
        responsavel="Carlos Mendes",
        status="Aberta",
        valor_mao_de_obra=15000.00,
    )

    os_1045 = OrdemServico(
        numero="OS-1045",
        cliente_id=cli_0244.id,
        titulo_resumo="Escada de acesso NR-12",
        tipo_servico="Serralheria industrial",
        data_abertura="10/06/2025",
        prazo_entrega="19/06/2025",
        responsavel="André Souza",
        status="Concluída",
        valor_mao_de_obra=3800.00,
    )

    os_1044 = OrdemServico(
        numero="OS-1044",
        cliente_id=cli_0243.id,
        titulo_resumo="Reforço estrutural",
        tipo_servico="Manutenção industrial",
        data_abertura="09/06/2025",
        prazo_entrega="25/06/2025",
        responsavel="Bruno Lima",
        status="Em andamento",
        valor_mao_de_obra=6100.00,
    )

    os_0984 = OrdemServico(
        numero="OS-0984",
        cliente_id=cli_0248.id,
        titulo_resumo="Reforço em plataforma industrial",
        descricao_detalhada="Reforço em plataforma industrial",
        tipo_servico="Manutenção industrial",
        data_abertura="18/04/2025",
        prazo_entrega="30/04/2025",
        responsavel="Carlos Mendes",
        status="Concluída",
        valor_mao_de_obra=5400.00,
    )

    os_0912 = OrdemServico(
        numero="OS-0912",
        cliente_id=cli_0248.id,
        titulo_resumo="Fabricação de guarda-corpo NR-12",
        descricao_detalhada="Fabricação de guarda-corpo NR-12",
        tipo_servico="Serralheria industrial",
        data_abertura="02/02/2025",
        prazo_entrega="15/02/2025",
        responsavel="André Souza",
        status="Concluída",
        valor_mao_de_obra=3200.00,
    )

    db.session.add_all([os_1048, os_1047, os_1046, os_1045, os_1044, os_0984, os_0912])
    db.session.commit()

