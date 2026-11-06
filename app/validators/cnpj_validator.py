import re
from typing import Any, Mapping, Optional, Tuple

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CnpjValidator:
    """Responsável pela normalização e validação fiscal oficial (CPF/CNPJ) e de contato (Telefone/E-mail)."""

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
    def validar_cpf(cls, cpf: str | None) -> bool:
        """Valida CPF (11 dígitos) pelo algoritmo oficial de dígitos verificadores da Receita Federal."""
        digitos = cls.normalizar_documento(cpf)
        if len(digitos) != 11 or digitos == digitos[0] * 11:
            return False

        soma1 = sum(int(digitos[i]) * (10 - i) for i in range(9))
        resto1 = soma1 % 11
        dv1 = 0 if resto1 < 2 else 11 - resto1
        if int(digitos[9]) != dv1:
            return False

        soma2 = sum(int(digitos[i]) * (11 - i) for i in range(10))
        resto2 = soma2 % 11
        dv2 = 0 if resto2 < 2 else 11 - resto2
        return int(digitos[10]) == dv2

    @classmethod
    def validar_cnpj(cls, cnpj: str | None) -> bool:
        """Valida CNPJ (14 dígitos) pelo algoritmo oficial de dígitos verificadores da Receita Federal."""
        digitos = cls.normalizar_documento(cnpj)
        if len(digitos) != 14 or digitos == digitos[0] * 14:
            return False

        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma1 = sum(int(digitos[i]) * pesos1[i] for i in range(12))
        resto1 = soma1 % 11
        dv1 = 0 if resto1 < 2 else 11 - resto1
        if int(digitos[12]) != dv1:
            return False

        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma2 = sum(int(digitos[i]) * pesos2[i] for i in range(13))
        resto2 = soma2 % 11
        dv2 = 0 if resto2 < 2 else 11 - resto2
        return int(digitos[13]) == dv2

    @classmethod
    def validar_telefone(cls, telefone: str | None) -> Optional[str]:
        """Valida telefone (10 ou 11 dígitos numéricos com DDD) quando informado e retorna formatado."""
        texto = (telefone or "").strip()
        if not texto:
            return None

        digitos = re.sub(r"\D", "", texto)
        if len(digitos) not in (10, 11):
            raise ValueError(
                "Telefone inválido. Informe o DDD e o número completo (10 ou 11 dígitos)."
            )

        if len(digitos) == 11:
            return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"

    @classmethod
    def validar_email(cls, email: str | None) -> Optional[str]:
        """Valida endereço de e-mail via Regex quando informado."""
        texto = (email or "").strip()
        if not texto:
            return None

        if not EMAIL_REGEX.match(texto):
            raise ValueError(
                "E-mail inválido. Informe um endereço completo (ex: contato@empresa.com.br)."
            )
        return texto

    @classmethod
    def validar_dados_obrigatorios(cls, dados: Mapping[str, Any]) -> Tuple[str, str]:
        """Valida razão social/nome, tipo de pessoa + CPF/CNPJ real e contato (telefone/e-mail)."""
        razao_social = (dados.get("razao_social") or "").strip()
        cpf_cnpj_bruto = (dados.get("cpf_cnpj") or "").strip()
        tipo_pessoa = (dados.get("tipo_pessoa") or "Pessoa jurídica").strip()

        if not razao_social:
            raise ValueError("O campo Razão Social / Nome é obrigatório.")

        if not cpf_cnpj_bruto:
            raise ValueError("O campo CPF / CNPJ é obrigatório.")

        digitos = cls.normalizar_documento(cpf_cnpj_bruto)

        if tipo_pessoa == "Pessoa física":
            if len(digitos) != 11 or not cls.validar_cpf(digitos):
                raise ValueError(
                    "CPF inválido para Pessoa Física. Informe um CPF real com 11 dígitos."
                )
        else:
            if len(digitos) != 14 or not cls.validar_cnpj(digitos):
                raise ValueError(
                    "CNPJ inválido para Pessoa Jurídica. Informe um CNPJ real com 14 dígitos."
                )

        cls.validar_telefone(dados.get("telefone"))
        cls.validar_email(dados.get("email"))

        return razao_social, cls.formatar_documento(digitos)


def limpar_documento(documento: str) -> str:
    return CnpjValidator.normalizar_documento(documento)


def validar_cpf(cpf: str) -> bool:
    return CnpjValidator.validar_cpf(cpf)


def validar_cnpj(cnpj: str) -> bool:
    return CnpjValidator.validar_cnpj(cnpj)
