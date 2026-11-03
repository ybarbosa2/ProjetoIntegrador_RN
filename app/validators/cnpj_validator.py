import re
from typing import Any, Mapping, Tuple


class CnpjValidator:
    """Responsável pela normalização, validação estrutural e obrigatoriedade fiscal (CPF/CNPJ)."""

    @staticmethod
    def normalizar_documento(doc: str | None) -> str:
        """Remove pontuações e espaços, mantendo apenas dígitos numéricos."""
        return re.sub(r"\D", "", doc or "")

    @classmethod
    def formatar_documento(cls, doc: str | None) -> str:
        """Formata 11 dígitos como CPF e 14 dígitos como CNPJ."""
        digitos = cls.normalizar_documento(doc)
        if len(digitos) == 14:
            return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
        if len(digitos) == 11:
            return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
        return (doc or "").strip()

    @classmethod
    def validar_dados_obrigatorios(cls, dados: Mapping[str, Any]) -> Tuple[str, str]:
        """Valida razão social/nome e formato de CPF/CNPJ, retornando (razao_social, documento_formatado)."""
        razao_social = (dados.get("razao_social") or "").strip()
        cpf_cnpj_bruto = (dados.get("cpf_cnpj") or "").strip()

        if not razao_social:
            raise ValueError("O campo Razão Social / Nome é obrigatório.")

        if not cpf_cnpj_bruto:
            raise ValueError("O campo CPF / CNPJ é obrigatório.")

        digitos = cls.normalizar_documento(cpf_cnpj_bruto)
        if len(digitos) not in (11, 14) or digitos == digitos[0] * len(digitos):
            raise ValueError("Formato de CPF ou CNPJ inválido. Informe 11 ou 14 dígitos.")

        return razao_social, cls.formatar_documento(digitos)


def limpar_documento(documento: str) -> str:
    return CnpjValidator.normalizar_documento(documento)


def validar_cnpj(cnpj: str) -> bool:
    digitos = CnpjValidator.normalizar_documento(cnpj)
    return len(digitos) == 14 and digitos != digitos[0] * 14
