import re
from typing import List, Optional

from app.database import db
from app.models.cliente import Cliente


class ClienteRepository:
    """Camada de acesso a dados para Clientes."""

    @staticmethod
    def listar_todos(
        busca: Optional[str] = None,
        situacao: Optional[str] = None,
        ordenar_por_nome: bool = False,
    ) -> List[Cliente]:
        query = Cliente.query

        if situacao and situacao not in ("Todos", "todos", ""):
            if situacao.lower().startswith("ativ"):
                query = query.filter(Cliente.situacao == "Ativo")
            elif situacao.lower().startswith("inativ"):
                query = query.filter(Cliente.situacao == "Inativo")
            else:
                query = query.filter(Cliente.situacao == situacao)

        if busca and busca.strip():
            termo = f"%{busca.strip()}%"
            digitos = re.sub(r"\D", "", busca.strip())
            condicoes = [
                Cliente.razao_social.ilike(termo),
                Cliente.nome_fantasia.ilike(termo),
                Cliente.codigo.ilike(termo),
                Cliente.cpf_cnpj.ilike(termo),
            ]
            if digitos:
                coluna_limpa = db.func.replace(
                    db.func.replace(
                        db.func.replace(Cliente.cpf_cnpj, ".", ""),
                        "/",
                        "",
                    ),
                    "-",
                    "",
                )
                condicoes.append(coluna_limpa.ilike(f"%{digitos}%"))
            query = query.filter(db.or_(*condicoes))

        if ordenar_por_nome:
            return query.order_by(Cliente.razao_social.asc()).all()
        return query.order_by(Cliente.codigo.desc()).all()

    @staticmethod
    def buscar_por_id(cliente_id: int) -> Optional[Cliente]:
        return db.session.get(Cliente, cliente_id)

    @staticmethod
    def buscar_por_cpf_cnpj(cpf_cnpj: str) -> Optional[Cliente]:
        if not cpf_cnpj or not cpf_cnpj.strip():
            return None

        texto = cpf_cnpj.strip()
        digitos = re.sub(r"\D", "", texto)

        if not digitos:
            return Cliente.query.filter_by(cpf_cnpj=texto).first()

        coluna_limpa = db.func.replace(
            db.func.replace(
                db.func.replace(
                    db.func.replace(Cliente.cpf_cnpj, ".", ""),
                    "/",
                    "",
                ),
                "-",
                "",
            ),
            " ",
            "",
        )
        return Cliente.query.filter(
            db.or_(Cliente.cpf_cnpj == texto, coluna_limpa == digitos)
        ).first()

    @staticmethod
    def gerar_proximo_codigo() -> str:
        codigos = [row[0] for row in db.session.query(Cliente.codigo).all() if row[0]]
        maior_numero = 0
        for codigo in codigos:
            match = re.search(r"(\d+)$", codigo)
            if match:
                maior_numero = max(maior_numero, int(match.group(1)))
        return f"CLI-{maior_numero + 1:04d}"

    @staticmethod
    def salvar(cliente: Cliente) -> Cliente:
        db.session.add(cliente)
        db.session.commit()
        return cliente

    @staticmethod
    def excluir(cliente: Cliente) -> None:
        db.session.delete(cliente)
        db.session.commit()

    @staticmethod
    def contar_todos() -> int:
        return Cliente.query.count()

    @staticmethod
    def contar_ativos() -> int:
        return Cliente.query.filter_by(situacao="Ativo").count()

    @staticmethod
    def contar_inativos() -> int:
        return Cliente.query.filter_by(situacao="Inativo").count()
