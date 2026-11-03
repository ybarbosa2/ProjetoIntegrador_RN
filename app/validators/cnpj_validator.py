import re


def limpar_documento(documento: str) -> str:
    """Remove caracteres não numéricos de CPF ou CNPJ."""
    return re.sub(r"\D", "", documento or "")


def validar_cnpj(cnpj: str) -> bool:
    """Valida os dígitos verificadores de um CNPJ brasileiro."""
    numeros = limpar_documento(cnpj)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False

    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_1 = sum(int(d) * p for d, p in zip(numeros[:12], pesos_1))
    resto_1 = soma_1 % 11
    digito_1 = 0 if resto_1 < 2 else 11 - resto_1

    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_2 = sum(int(d) * p for d, p in zip(numeros[:13], pesos_2))
    resto_2 = soma_2 % 11
    digito_2 = 0 if resto_2 < 2 else 11 - resto_2

    return numeros[-2:] == f"{digito_1}{digito_2}"

