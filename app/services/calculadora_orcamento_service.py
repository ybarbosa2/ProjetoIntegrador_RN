from typing import Iterable, Mapping


class CalculadoraOrcamentoService:
    """Serviço responsável pelo cálculo padronizado de orçamentos de Ordens de Serviço."""

    @staticmethod
    def calcular_total_materiais(itens: Iterable[Mapping[str, float]]) -> float:
        return float(
            sum(
                float(item.get("quantidade", 0.0)) * float(item.get("valor_unitario", 0.0))
                for item in itens
            )
        )

    @classmethod
    def calcular_orcamento_total(
        cls,
        valor_mao_de_obra: float,
        itens: Iterable[Mapping[str, float]],
    ) -> float:
        return float(valor_mao_de_obra or 0.0) + cls.calcular_total_materiais(itens)

