from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.cliente import Cliente
from app.repositories.cliente_repository import ClienteRepository


class ClienteService:
    """Regras de negócio do módulo de Clientes."""

    def __init__(self, repository: ClienteRepository | None = None) -> None:
        self.repository = repository or ClienteRepository()

    def listar_clientes(
        self,
        busca: Optional[str] = None,
        situacao: Optional[str] = None,
    ) -> List[Cliente]:
        return self.repository.listar_todos(busca=busca, situacao=situacao)

    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        return self.repository.buscar_por_id(cliente_id)

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.repository.contar_todos(),
            "ativos": self.repository.contar_ativos(),
            "inativos": self.repository.contar_inativos(),
        }

    def cadastrar_cliente(self, dados: Dict[str, Any]) -> Cliente:
        razao_social = (dados.get("razao_social") or "").strip()
        cpf_cnpj = (dados.get("cpf_cnpj") or "").strip()

        if not razao_social:
            raise ValueError("O campo Razão Social / Nome é obrigatório.")
        if not cpf_cnpj:
            raise ValueError("O campo CPF / CNPJ é obrigatório.")

        existente = self.repository.buscar_por_cpf_cnpj(cpf_cnpj)
        if existente is not None:
            raise ValueError("Este CNPJ já está cadastrado no sistema")

        agora = datetime.now()
        novo_cliente = Cliente(
            codigo=self.repository.gerar_proximo_codigo(),
            tipo_pessoa=(dados.get("tipo_pessoa") or "Pessoa jurídica").strip(),
            razao_social=razao_social,
            nome_fantasia=(dados.get("nome_fantasia") or "").strip() or None,
            cpf_cnpj=cpf_cnpj,
            inscricao_estadual=(dados.get("inscricao_estadual") or "").strip() or None,
            situacao=(dados.get("situacao") or "Ativo").strip(),
            telefone=(dados.get("telefone") or "").strip() or None,
            email=(dados.get("email") or "").strip() or None,
            cep=(dados.get("cep") or "").strip() or None,
            endereco=(dados.get("endereco") or "").strip() or None,
            numero=(dados.get("numero") or "").strip() or None,
            complemento=(dados.get("complemento") or "").strip() or None,
            bairro=(dados.get("bairro") or "").strip() or None,
            cidade=(dados.get("cidade") or "").strip() or None,
            estado=(dados.get("estado") or "").strip() or None,
            observacoes=(dados.get("observacoes") or "").strip() or None,
            data_cadastro=dados.get("data_cadastro") or agora.strftime("%d/%m/%Y"),
            ultima_atualizacao=agora.strftime("%d/%m/%Y às %H:%M"),
        )
        return self.repository.salvar(novo_cliente)

    def atualizar_cliente(self, cliente_id: int, dados: Dict[str, Any]) -> Cliente:
        cliente = self.repository.buscar_por_id(cliente_id)
        if cliente is None:
            raise ValueError("Cliente não encontrado.")

        razao_social = (dados.get("razao_social") or "").strip()
        cpf_cnpj = (dados.get("cpf_cnpj") or "").strip()

        if not razao_social:
            raise ValueError("O campo Razão Social / Nome é obrigatório.")
        if not cpf_cnpj:
            raise ValueError("O campo CPF / CNPJ é obrigatório.")

        existente = self.repository.buscar_por_cpf_cnpj(cpf_cnpj)
        if existente is not None and existente.id != cliente.id:
            raise ValueError("Este CNPJ já está cadastrado no sistema")

        cliente.tipo_pessoa = (dados.get("tipo_pessoa") or cliente.tipo_pessoa or "Pessoa jurídica").strip()
        cliente.razao_social = razao_social
        cliente.nome_fantasia = (dados.get("nome_fantasia") or "").strip() or None
        cliente.cpf_cnpj = cpf_cnpj
        cliente.inscricao_estadual = (dados.get("inscricao_estadual") or "").strip() or None
        cliente.situacao = (dados.get("situacao") or cliente.situacao or "Ativo").strip()
        cliente.telefone = (dados.get("telefone") or "").strip() or None
        cliente.email = (dados.get("email") or "").strip() or None
        cliente.cep = (dados.get("cep") or "").strip() or None
        cliente.endereco = (dados.get("endereco") or "").strip() or None
        cliente.numero = (dados.get("numero") or "").strip() or None
        cliente.complemento = (dados.get("complemento") or "").strip() or None
        cliente.bairro = (dados.get("bairro") or "").strip() or None
        cliente.cidade = (dados.get("cidade") or "").strip() or None
        cliente.estado = (dados.get("estado") or "").strip() or None
        cliente.observacoes = (dados.get("observacoes") or "").strip() or None
        cliente.ultima_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

        return self.repository.salvar(cliente)

    def excluir_cliente(self, cliente_id: int) -> str:
        cliente = self.repository.buscar_por_id(cliente_id)
        if cliente is None:
            raise ValueError("Cliente não encontrado.")

        if cliente.ordens_servico:
            cliente.situacao = "Inativo"
            cliente.ultima_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")
            self.repository.salvar(cliente)
            return "inativado"

        self.repository.excluir(cliente)
        return "excluido"
