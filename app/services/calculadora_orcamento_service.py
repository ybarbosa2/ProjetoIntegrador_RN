import re
from typing import Any, Dict, Iterable, List, Mapping

from app.models.ordem_servico import OrdemServico


class CalculadoraOrcamentoService:
    """Serviço especializado para cálculo e geração do Orçamento Comercial Padronizado (Seção 5.7)."""

    @staticmethod
    def calcular_subtotal_item(quantidade: float | int, valor_unitario: float | int) -> float:
        return round(float(quantidade or 0.0) * float(valor_unitario or 0.0), 2)

    @classmethod
    def calcular_totais_os(cls, ordem_servico: OrdemServico) -> Dict[str, float]:
        valor_materiais = round(
            sum(
                cls.calcular_subtotal_item(item.quantidade, item.valor_unitario)
                for item in (ordem_servico.itens or [])
            ),
            2,
        )
        valor_mao_de_obra = round(float(ordem_servico.valor_mao_de_obra or 0.0), 2)
        valor_total = round(valor_materiais + valor_mao_de_obra, 2)

        return {
            "valor_materiais": valor_materiais,
            "valor_mao_de_obra": valor_mao_de_obra,
            "valor_total": valor_total,
        }

    @classmethod
    def gerar_dados_orcamento(
        cls,
        ordem_servico: OrdemServico,
        desconto: float = 0.0,
        condicoes_pagamento: str = "28 dias via boleto/PIX",
        validade: str = "15 dias",
    ) -> Dict[str, Any]:
        if ordem_servico is None:
            raise ValueError("Ordem de serviço inválida para geração de orçamento.")

        match_num = re.search(r"(\d+)$", ordem_servico.numero or "")
        sufixo = match_num.group(1) if match_num else f"{ordem_servico.id or 1:04d}"
        codigo_orcamento = f"ORC-{sufixo}"

        cliente = ordem_servico.cliente
        dados_cliente = {
            "id": cliente.id if cliente else None,
            "codigo": cliente.codigo if cliente else "",
            "razao_social": cliente.razao_social if cliente else "",
            "nome_fantasia": (cliente.nome_fantasia or cliente.razao_social) if cliente else "",
            "cpf_cnpj": cliente.cpf_cnpj if cliente else "",
            "inscricao_estadual": (cliente.inscricao_estadual or "Isento") if cliente else "Isento",
            "telefone": (cliente.telefone or "Não informado") if cliente else "Não informado",
            "email": (cliente.email or "Não informado") if cliente else "Não informado",
            "endereco_completo": (
                cliente.endereco_completo_formatado or "Não informado"
            )
            if cliente
            else "Não informado",
        }

        itens_detalhados: List[Dict[str, Any]] = []
        for item in ordem_servico.itens or []:
            material = item.material
            subtotal = cls.calcular_subtotal_item(item.quantidade, item.valor_unitario)
            itens_detalhados.append(
                {
                    "material_id": item.material_id,
                    "codigo": material.codigo if material else "",
                    "descricao": material.descricao if material else "",
                    "unidade": material.unidade if material else "UN",
                    "quantidade": float(item.quantidade),
                    "valor_unitario": round(float(item.valor_unitario), 2),
                    "subtotal": subtotal,
                }
            )

        totais = cls.calcular_totais_os(ordem_servico)
        valor_desconto = round(max(0.0, float(desconto or 0.0)), 2)
        valor_total_final = round(max(0.0, totais["valor_total"] - valor_desconto), 2)

        return {
            "codigo_orcamento": codigo_orcamento,
            "numero_os": ordem_servico.numero,
            "os_id": ordem_servico.id,
            "data_emissao": ordem_servico.data_abertura,
            "prazo_entrega": ordem_servico.prazo_entrega,
            "status_os": ordem_servico.status,
            "cliente": dados_cliente,
            "servico": {
                "titulo_resumo": ordem_servico.titulo_resumo or ordem_servico.tipo_servico,
                "tipo_servico": ordem_servico.tipo_servico or "Serviço industrial",
                "quantidade_servico": ordem_servico.quantidade_servico or "1 conjunto",
                "responsavel": ordem_servico.responsavel or "Carlos Mendes",
                "descricao_detalhada": ordem_servico.descricao_detalhada or "",
                "especificacoes_tecnicas": ordem_servico.especificacoes_tecnicas or "",
            },
            "itens": itens_detalhados,
            "valor_materiais": totais["valor_materiais"],
            "valor_mao_de_obra": totais["valor_mao_de_obra"],
            "desconto": valor_desconto,
            "valor_total": valor_total_final,
            "condicoes_pagamento": condicoes_pagamento,
            "validade": validade,
        }

    @classmethod
    def calcular_total_materiais(cls, itens: Iterable[Mapping[str, float]]) -> float:
        return round(
            sum(
                cls.calcular_subtotal_item(
                    item.get("quantidade", 0.0),
                    item.get("valor_unitario", 0.0),
                )
                for item in itens
            ),
            2,
        )

    @classmethod
    def calcular_orcamento_total(
        cls,
        valor_mao_de_obra: float,
        itens: Iterable[Mapping[str, float]],
    ) -> float:
        return round(float(valor_mao_de_obra or 0.0) + cls.calcular_total_materiais(itens), 2)
