from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from app.models.ordem_servico import ItemOrdemServico, OrdemServico
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.os_repository import OsRepository
from app.services.calculadora_orcamento_service import CalculadoraOrcamentoService
from app.services.estoque_service import EstoqueService


def _parse_valor_monetario(valor: Any, nome_campo: str = "Valor") -> float:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return 0.0
    if isinstance(valor, (int, float)):
        num = float(valor)
    else:
        texto = str(valor).replace("R$", "").strip()
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")
        try:
            num = float(texto)
        except ValueError as exc:
            raise ValueError(f"Valor inválido em {nome_campo}.") from exc
    if num < 0:
        raise ValueError(f"{nome_campo} não pode ser negativo.")
    return round(num, 2)


class OsService:
    """Regras de negócio do módulo de Ordens de Serviço e integração com Clientes, Estoque e Orçamentos."""

    def __init__(
        self,
        os_repository: OsRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
        estoque_service: EstoqueService | None = None,
        calculadora_service: CalculadoraOrcamentoService | None = None,
    ) -> None:
        self.os_repository = os_repository or OsRepository()
        self.cliente_repository = cliente_repository or ClienteRepository()
        self.estoque_service = estoque_service or EstoqueService()
        self.calculadora_service = calculadora_service or CalculadoraOrcamentoService()

    @property
    def repository(self) -> OsRepository:
        return self.os_repository

    def listar_ordens(
        self,
        busca: Optional[str] = None,
        status: Optional[str] = None,
        cliente_id: Optional[int | str] = None,
        periodo: Optional[str] = None,
    ) -> List[OrdemServico]:
        return self.os_repository.listar_todas(
            busca=busca,
            status=status,
            cliente_id=cliente_id,
            periodo=periodo,
        )

    def buscar_por_id(self, os_id: int) -> Optional[OrdemServico]:
        return self.os_repository.buscar_por_id(os_id)

    def gerar_proximo_numero(self) -> str:
        return self.os_repository.gerar_proximo_numero()

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.os_repository.contar_todas(),
            "ativas": self.os_repository.contar_ativas(),
            "em_andamento": self.os_repository.contar_em_andamento(),
        }

    def gerar_orcamento(
        self,
        os_id_ou_obj: int | OrdemServico,
        desconto: float = 0.0,
    ) -> Dict[str, Any]:
        ordem = (
            os_id_ou_obj
            if isinstance(os_id_ou_obj, OrdemServico)
            else self.os_repository.buscar_por_id(int(os_id_ou_obj))
        )
        if ordem is None:
            raise ValueError("Ordem de Serviço não encontrada.")
        return self.calculadora_service.gerar_dados_orcamento(ordem, desconto=desconto)

    def criar_ordem_servico(
        self,
        dados: Mapping[str, Any],
        lista_materiais: Optional[List[Mapping[str, Any]]] = None,
    ) -> OrdemServico:
        # RN03 / CT03 / UC01-E1: Cliente obrigatório
        cliente_id_bruto = dados.get("cliente_id")
        if cliente_id_bruto is None or str(cliente_id_bruto).strip() == "":
            raise ValueError("Cliente obrigatório não selecionado")

        try:
            cliente_id = int(cliente_id_bruto)
        except (TypeError, ValueError) as exc:
            raise ValueError("Cliente obrigatório não selecionado") from exc

        cliente = self.cliente_repository.buscar_por_id(cliente_id)
        if cliente is None:
            raise ValueError("Cliente obrigatório não selecionado")

        tipo_servico = (dados.get("tipo_servico") or "").strip()
        descricao_detalhada = (dados.get("descricao_detalhada") or "").strip()
        titulo_resumo = (dados.get("titulo_resumo") or "").strip()

        if not tipo_servico and not descricao_detalhada and not titulo_resumo:
            raise ValueError("Informe o tipo ou a descrição do serviço da Ordem de Serviço.")

        if not titulo_resumo:
            base_resumo = descricao_detalhada or tipo_servico
            titulo_resumo = base_resumo[:80] + ("..." if len(base_resumo) > 80 else "")

        numero_informado = (dados.get("numero") or "").strip().lstrip("#").upper()
        numero_os = numero_informado or self.os_repository.gerar_proximo_numero()

        if self.os_repository.buscar_por_numero(numero_os) is not None:
            raise ValueError(f"O número {numero_os} já está em uso por outra Ordem de Serviço.")

        hoje = datetime.now()
        data_abertura = (dados.get("data_abertura") or "").strip() or hoje.strftime("%d/%m/%Y")
        # Prazo de entrega opcional (pode permanecer em branco)
        prazo_entrega = (dados.get("prazo_entrega") or "").strip()
        status = (dados.get("status") or "Aberta").strip()
        quantidade_servico = (dados.get("quantidade_servico") or "1 conjunto").strip()
        responsavel = (dados.get("responsavel") or "Carlos Mendes").strip()
        especificacoes_tecnicas = (dados.get("especificacoes_tecnicas") or "").strip() or None
        valor_mao_de_obra = _parse_valor_monetario(
            dados.get("valor_mao_de_obra", 0.0),
            "Valor da mão de obra",
        )

        if lista_materiais is None and "itens" in dados:
            lista_materiais = dados.get("itens")

        # Pré-validação de todos os materiais solicitados antes de realizar baixas (evita baixa parcial)
        materiais_validados: List[tuple[Any, float]] = []
        for item_req in lista_materiais or []:
            mat_id_raw = item_req.get("material_id")
            qtd_raw = item_req.get("quantidade")
            if mat_id_raw is None or str(mat_id_raw).strip() == "":
                continue
            qtd = _parse_valor_monetario(qtd_raw, "Quantidade do material")
            if qtd <= 0:
                continue

            material = self.estoque_service.buscar_por_id(int(mat_id_raw))
            if material is None:
                raise ValueError(f"Material ID {mat_id_raw} não encontrado no estoque.")

            if qtd > float(material.disponivel or 0.0):
                raise ValueError("Saldo insuficiente no estoque")

            materiais_validados.append((material, qtd))

        # Baixa automática no estoque (RN02 + RF04) e criação dos itens da O.S.
        itens_os: List[ItemOrdemServico] = []
        for material, qtd in materiais_validados:
            self.estoque_service.registrar_saida(
                material,
                quantidade=qtd,
                responsavel=responsavel,
                descricao_movimentacao=f"Saída para {numero_os}",
            )
            itens_os.append(
                ItemOrdemServico(
                    material_id=material.id,
                    quantidade=qtd,
                    valor_unitario=float(material.custo_unitario or 0.0),
                )
            )

        nova_os = OrdemServico(
            numero=numero_os,
            cliente_id=cliente.id,
            data_abertura=data_abertura,
            prazo_entrega=prazo_entrega,
            status=status,
            titulo_resumo=titulo_resumo,
            tipo_servico=tipo_servico or "Serviço industrial",
            quantidade_servico=quantidade_servico,
            responsavel=responsavel,
            descricao_detalhada=descricao_detalhada or titulo_resumo,
            especificacoes_tecnicas=especificacoes_tecnicas,
            valor_mao_de_obra=valor_mao_de_obra,
            itens=itens_os,
        )

        return self.os_repository.salvar(nova_os)

    def _sincronizar_itens_estoque(
        self,
        ordem: OrdemServico,
        lista_materiais: List[Mapping[str, Any]],
    ) -> None:
        """Sincroniza itens da O.S. com o estoque: devolve reduções/remoções e baixa acréscimos/novos."""
        qtd_atual_por_mat: Dict[int, float] = {}
        preco_atual_por_mat: Dict[int, float] = {}
        for item_existente in ordem.itens or []:
            mid = int(item_existente.material_id)
            qtd_atual_por_mat[mid] = round(
                qtd_atual_por_mat.get(mid, 0.0) + float(item_existente.quantidade or 0.0),
                4,
            )
            preco_atual_por_mat[mid] = float(item_existente.valor_unitario or 0.0)

        qtd_nova_por_mat: Dict[int, float] = {}
        ordem_materiais: List[int] = []
        for item_req in lista_materiais:
            mat_id_raw = item_req.get("material_id")
            qtd_raw = item_req.get("quantidade")
            if mat_id_raw is None or str(mat_id_raw).strip() == "":
                continue
            qtd = _parse_valor_monetario(qtd_raw, "Quantidade do material")
            if qtd <= 0:
                continue
            mid = int(mat_id_raw)
            if mid not in qtd_nova_por_mat:
                ordem_materiais.append(mid)
                qtd_nova_por_mat[mid] = 0.0
            qtd_nova_por_mat[mid] = round(qtd_nova_por_mat[mid] + qtd, 4)

        # 1. Pré-validação de existência e disponibilidade de saldo para todos os acréscimos
        for mid in ordem_materiais:
            material = self.estoque_service.buscar_por_id(mid)
            if material is None:
                raise ValueError(f"Material ID {mid} não encontrado no estoque.")
            delta = round(qtd_nova_por_mat[mid] - qtd_atual_por_mat.get(mid, 0.0), 4)
            if delta > 0 and delta > float(material.disponivel or 0.0):
                raise ValueError("Saldo insuficiente no estoque")

        responsavel = ordem.responsavel or "Carlos Mendes"

        # 2. Devolve ao estoque itens removidos ou com quantidade reduzida
        for mid, qtd_antiga in qtd_atual_por_mat.items():
            qtd_nova = qtd_nova_por_mat.get(mid, 0.0)
            delta = round(qtd_nova - qtd_antiga, 4)
            if delta < 0:
                material = self.estoque_service.buscar_por_id(mid)
                if material is not None:
                    self.estoque_service.registrar_entrada(
                        material,
                        quantidade=abs(delta),
                        responsavel=responsavel,
                        descricao_movimentacao=f"Estorno de edição da {ordem.numero}",
                    )

        # 3. Realiza baixa no estoque para itens novos ou com quantidade aumentada
        for mid in ordem_materiais:
            qtd_antiga = qtd_atual_por_mat.get(mid, 0.0)
            qtd_nova = qtd_nova_por_mat[mid]
            delta = round(qtd_nova - qtd_antiga, 4)
            if delta > 0:
                material = self.estoque_service.buscar_por_id(mid)
                self.estoque_service.registrar_saida(
                    material,
                    quantidade=delta,
                    responsavel=responsavel,
                    descricao_movimentacao=f"Saída para {ordem.numero}",
                )

        # 4. Reconstrói a lista de itens da O.S. e recalcula os totais via CalculadoraOrcamentoService
        novos_itens: List[ItemOrdemServico] = []
        for mid in ordem_materiais:
            material = self.estoque_service.buscar_por_id(mid)
            valor_unit = preco_atual_por_mat.get(
                mid,
                float(material.custo_unitario or 0.0) if material else 0.0,
            )
            novos_itens.append(
                ItemOrdemServico(
                    material_id=mid,
                    quantidade=qtd_nova_por_mat[mid],
                    valor_unitario=valor_unit,
                )
            )
        ordem.itens = novos_itens
        self.calculadora_service.calcular_totais_os(ordem)

    def atualizar_status_ou_dados(
        self,
        os_id: int,
        dados: Mapping[str, Any],
        lista_materiais: Optional[List[Mapping[str, Any]]] = None,
    ) -> OrdemServico:
        ordem = self.os_repository.buscar_por_id(os_id)
        if ordem is None:
            raise ValueError("Ordem de Serviço não encontrada.")

        if "cliente_id" in dados and str(dados.get("cliente_id", "")).strip() != "":
            cliente = self.cliente_repository.buscar_por_id(int(dados["cliente_id"]))
            if cliente is None:
                raise ValueError("Cliente obrigatório não selecionado")
            ordem.cliente_id = cliente.id

        if "status" in dados and (dados.get("status") or "").strip():
            ordem.status = dados["status"].strip()
        if "data_abertura" in dados and (dados.get("data_abertura") or "").strip():
            ordem.data_abertura = dados["data_abertura"].strip()
        if "prazo_entrega" in dados:
            ordem.prazo_entrega = (dados.get("prazo_entrega") or "").strip()
        if "titulo_resumo" in dados and (dados.get("titulo_resumo") or "").strip():
            ordem.titulo_resumo = dados["titulo_resumo"].strip()
        if "tipo_servico" in dados and (dados.get("tipo_servico") or "").strip():
            ordem.tipo_servico = dados["tipo_servico"].strip()
        if "quantidade_servico" in dados and (dados.get("quantidade_servico") or "").strip():
            ordem.quantidade_servico = dados["quantidade_servico"].strip()
        if "responsavel" in dados and (dados.get("responsavel") or "").strip():
            ordem.responsavel = dados["responsavel"].strip()
        if "descricao_detalhada" in dados:
            texto_desc = (dados.get("descricao_detalhada") or "").strip()
            if texto_desc:
                ordem.descricao_detalhada = texto_desc
        if "especificacoes_tecnicas" in dados:
            ordem.especificacoes_tecnicas = (
                dados.get("especificacoes_tecnicas") or ""
            ).strip() or None
        if "valor_mao_de_obra" in dados and str(dados.get("valor_mao_de_obra", "")).strip() != "":
            ordem.valor_mao_de_obra = _parse_valor_monetario(
                dados.get("valor_mao_de_obra"),
                "Valor da mão de obra",
            )

        if lista_materiais is None and "itens" in dados:
            lista_materiais = dados.get("itens")

        if lista_materiais is not None:
            self._sincronizar_itens_estoque(ordem, list(lista_materiais))

        self.calculadora_service.calcular_totais_os(ordem)
        return self.os_repository.salvar(ordem)

    atualizar_ordem_servico = atualizar_status_ou_dados


OSService = OsService
