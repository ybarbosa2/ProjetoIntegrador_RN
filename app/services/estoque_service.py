from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.material import Material, MovimentacaoEstoque
from app.repositories.estoque_repository import EstoqueRepository


def _converter_numero(valor: Any, nome_campo: str, obrigatorio_positivo: bool = False) -> float:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obrigatorio_positivo:
            raise ValueError(f"Informe um valor válido para {nome_campo}.")
        return 0.0

    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = str(valor).replace("R$", "").strip()
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")
        try:
            numero = float(texto)
        except ValueError as exc:
            raise ValueError(f"Valor numérico inválido em {nome_campo}.") from exc

    if obrigatorio_positivo and numero <= 0:
        raise ValueError(f"O campo {nome_campo} deve ser maior que zero.")
    if numero < 0:
        raise ValueError(f"O campo {nome_campo} não pode ser negativo.")
    return numero


class EstoqueService:
    """Regras de negócio do módulo de Controle de Estoque."""

    def __init__(self, repositorio: EstoqueRepository | None = None) -> None:
        self.repositorio = repositorio or EstoqueRepository()

    @property
    def repository(self) -> EstoqueRepository:
        return self.repositorio

    def _resolver_material(self, material_id_ou_obj: int | Material) -> Material:
        if isinstance(material_id_ou_obj, Material):
            return material_id_ou_obj
        material = self.repositorio.buscar_por_id(int(material_id_ou_obj))
        if material is None:
            raise ValueError("Material não encontrado.")
        return material

    def listar_materiais(
        self,
        busca: Optional[str] = None,
        categoria: Optional[str] = None,
    ) -> List[Material]:
        return self.repositorio.listar_todos(busca=busca, categoria=categoria)

    def buscar_por_id(self, material_id: int) -> Optional[Material]:
        return self.repositorio.buscar_por_id(material_id)

    def gerar_proximo_codigo(self) -> str:
        return self.repositorio.gerar_proximo_codigo()

    def listar_ultimas_movimentacoes(self, limite: int = 10) -> List[MovimentacaoEstoque]:
        return self.repositorio.listar_ultimas_movimentacoes(limite=limite)

    def listar_movimentacoes_por_material(self, material_id: int) -> List[MovimentacaoEstoque]:
        return self.repositorio.listar_movimentacoes_por_material(material_id)

    def registrar_entrada(
        self,
        material_id_ou_obj: int | Material,
        quantidade: float | str,
        responsavel: str = "Carlos Mendes",
        descricao_movimentacao: str = "Entrada de compra",
    ) -> Material:
        material = self._resolver_material(material_id_ou_obj)
        qtd = _converter_numero(quantidade, "Quantidade", obrigatorio_positivo=True)

        material.registrar_entrada(qtd)
        self.repositorio.salvar(material)

        movimentacao = MovimentacaoEstoque(
            material_id=material.id,
            data_hora=datetime.now().strftime("%d/%m/%Y · %H:%M"),
            tipo="Entrada",
            descricao_movimentacao=(descricao_movimentacao or "Entrada de compra").strip(),
            quantidade=qtd,
            responsavel=(responsavel or "Carlos Mendes").strip(),
        )
        self.repositorio.salvar_movimentacao(movimentacao)
        return material

    adicionar_entrada = registrar_entrada

    def registrar_saida(
        self,
        material_id_ou_obj: int | Material,
        quantidade: float | str,
        responsavel: str = "Carlos Mendes",
        descricao_movimentacao: str = "Consumo interno oficina",
    ) -> Material:
        material = self._resolver_material(material_id_ou_obj)
        qtd = _converter_numero(quantidade, "Quantidade", obrigatorio_positivo=True)

        # RN02: Lança ValueError("Saldo insuficiente no estoque") se qtd > material.disponivel
        material.registrar_saida(qtd)
        self.repositorio.salvar(material)

        movimentacao = MovimentacaoEstoque(
            material_id=material.id,
            data_hora=datetime.now().strftime("%d/%m/%Y · %H:%M"),
            tipo="Saída",
            descricao_movimentacao=(descricao_movimentacao or "Consumo interno oficina").strip(),
            quantidade=qtd,
            responsavel=(responsavel or "Carlos Mendes").strip(),
        )
        self.repositorio.salvar_movimentacao(movimentacao)
        return material

    def cadastrar_material(self, dados: Dict[str, Any]) -> Material:
        descricao = (dados.get("descricao") or "").strip()
        if not descricao:
            raise ValueError("O campo Nome ou Descrição do material é obrigatório.")

        codigo_informado = (dados.get("codigo") or "").strip().upper()
        codigo = codigo_informado or self.repositorio.gerar_proximo_codigo()

        if self.repositorio.buscar_por_codigo(codigo) is not None:
            raise ValueError(f"O código {codigo} já está cadastrado no estoque.")

        categoria = (dados.get("categoria") or "Chapas").strip()
        tipo_material = (dados.get("tipo_material") or "Aço carbono").strip()
        unidade = (dados.get("unidade") or "UN").strip().upper()

        quantidade_inicial = _converter_numero(
            dados.get("quantidade_inicial", dados.get("disponivel", 0)),
            "Quantidade Inicial",
        )
        minimo = _converter_numero(dados.get("minimo", 0), "Estoque Mínimo")
        custo_unitario = _converter_numero(dados.get("custo_unitario", 0), "Custo Unitário")

        subtitulo = (dados.get("subtitulo") or "").strip() or f"{tipo_material} · {categoria}"

        material = Material(
            codigo=codigo,
            descricao=descricao,
            subtitulo=subtitulo,
            categoria=categoria,
            tipo_material=tipo_material,
            unidade=unidade,
            disponivel=0.0,
            minimo=minimo,
            custo_unitario=custo_unitario,
            localizacao=(dados.get("localizacao") or "").strip() or None,
            controle_lote=(dados.get("controle_lote") or "Não utilizado").strip(),
            fornecedor=(dados.get("fornecedor") or "").strip() or None,
            situacao=(dados.get("situacao") or "Ativo").strip(),
            observacoes=(dados.get("observacoes") or "").strip() or None,
        )

        self.repositorio.salvar(material)

        if quantidade_inicial > 0:
            self.registrar_entrada(
                material,
                quantidade=quantidade_inicial,
                responsavel="Rafael Nogueira",
                descricao_movimentacao="Entrada inicial de cadastro",
            )

        return material

    def atualizar_material(self, material_id: int, dados: Dict[str, Any]) -> Material:
        material = self.repositorio.buscar_por_id(material_id)
        if material is None:
            raise ValueError("Material não encontrado.")

        descricao = (dados.get("descricao") or "").strip()
        if not descricao:
            raise ValueError("O campo Nome ou Descrição do material é obrigatório.")

        codigo_informado = (dados.get("codigo") or material.codigo).strip().upper()
        existente = self.repositorio.buscar_por_codigo(codigo_informado)
        if existente is not None and existente.id != material.id:
            raise ValueError(f"O código {codigo_informado} já está cadastrado no estoque.")

        material.codigo = codigo_informado
        material.descricao = descricao
        material.categoria = (dados.get("categoria") or material.categoria).strip()
        material.tipo_material = (dados.get("tipo_material") or material.tipo_material).strip()
        material.unidade = (dados.get("unidade") or material.unidade).strip().upper()
        if "subtitulo" in dados and (dados.get("subtitulo") or "").strip():
            material.subtitulo = dados["subtitulo"].strip()
        if "disponivel" in dados and str(dados.get("disponivel", "")).strip() != "":
            material.disponivel = _converter_numero(dados.get("disponivel"), "Quantidade Disponível")
        material.minimo = _converter_numero(dados.get("minimo", material.minimo), "Estoque Mínimo")
        material.custo_unitario = _converter_numero(
            dados.get("custo_unitario", material.custo_unitario),
            "Custo Unitário",
        )
        material.localizacao = (dados.get("localizacao") or "").strip() or None
        material.controle_lote = (dados.get("controle_lote") or material.controle_lote or "Não utilizado").strip()
        material.fornecedor = (dados.get("fornecedor") or "").strip() or None
        material.situacao = (dados.get("situacao") or material.situacao or "Ativo").strip()
        material.observacoes = (dados.get("observacoes") or "").strip() or None

        return self.repositorio.salvar(material)

    def obter_resumo(self) -> Dict[str, int]:
        return {
            "total": self.repositorio.contar_todos(),
            "estoque_baixo": self.repositorio.contar_alertas_estoque(),
        }

    def obter_indicadores_estoque(self) -> Dict[str, Any]:
        return {
            "total_itens": self.repositorio.contar_todos(),
            "total_categorias": self.repositorio.contar_categorias_distintas(),
            "valor_total_estoque": self.repositorio.calcular_valor_total_estoque(),
            "itens_baixo_estoque": self.repositorio.contar_alertas_estoque(),
            "total_movimentacoes": self.repositorio.contar_movimentacoes(),
        }
