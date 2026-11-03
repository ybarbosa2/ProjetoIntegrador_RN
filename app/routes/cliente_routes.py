from typing import Any, Dict

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.cliente import Cliente
from app.services.cliente_service import ClienteService

clientes_bp = Blueprint("clientes", __name__)


def _cliente_para_dict(cliente: Cliente) -> Dict[str, Any]:
    return {
        "tipo_pessoa": cliente.tipo_pessoa or "Pessoa jurídica",
        "razao_social": cliente.razao_social or "",
        "nome_fantasia": cliente.nome_fantasia or "",
        "cpf_cnpj": cliente.cpf_cnpj or "",
        "inscricao_estadual": cliente.inscricao_estadual or "",
        "situacao": cliente.situacao or "Ativo",
        "telefone": cliente.telefone or "",
        "email": cliente.email or "",
        "cep": cliente.cep or "",
        "endereco": cliente.endereco or "",
        "numero": cliente.numero or "",
        "complemento": cliente.complemento or "",
        "bairro": cliente.bairro or "",
        "cidade": cliente.cidade or "",
        "estado": cliente.estado or "",
        "observacoes": cliente.observacoes or "",
    }


@clientes_bp.route("/clientes", methods=["GET"])
def listar_clientes():
    busca = (request.args.get("q") or "").strip()
    situacao = (request.args.get("situacao") or "Todos").strip()

    if situacao not in ("Todos", "Ativo", "Inativo"):
        situacao = "Todos"

    service = ClienteService()
    clientes = service.listar_clientes(busca=busca, situacao=situacao)
    resumo = service.obter_resumo()

    return render_template(
        "clientes/lista.html",
        active_page="clientes",
        clientes=clientes,
        busca=busca,
        situacao_atual=situacao,
        resumo=resumo,
        total_clientes=resumo["total"],
    )


@clientes_bp.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    service = ClienteService()

    if request.method == "POST":
        dados = request.form.to_dict()
        try:
            cliente = service.cadastrar_cliente(dados)
            flash(f"Cliente {cliente.codigo} cadastrado com sucesso!", "success")
            return redirect(url_for("clientes.listar_clientes"))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "clientes/novo.html",
                active_page="clientes",
                modo_edicao=False,
                cliente=None,
                dados=dados,
            )

    return render_template(
        "clientes/novo.html",
        active_page="clientes",
        modo_edicao=False,
        cliente=None,
        dados={"tipo_pessoa": "Pessoa jurídica", "situacao": "Ativo"},
    )


@clientes_bp.route("/clientes/<int:id>", methods=["GET"])
def detalhe_cliente(id: int):
    service = ClienteService()
    cliente = service.buscar_por_id(id)
    if cliente is None:
        abort(404)

    ordens = sorted(
        cliente.ordens_servico,
        key=lambda os_item: os_item.numero or "",
        reverse=True,
    )

    return render_template(
        "clientes/detalhe.html",
        active_page="clientes",
        cliente=cliente,
        ordens=ordens,
    )


@clientes_bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
def editar_cliente(id: int):
    service = ClienteService()
    cliente = service.buscar_por_id(id)
    if cliente is None:
        abort(404)

    if request.method == "POST":
        dados = request.form.to_dict()
        try:
            service.atualizar_cliente(id, dados)
            flash("Dados do cliente atualizados com sucesso!", "success")
            return redirect(url_for("clientes.detalhe_cliente", id=id))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "clientes/novo.html",
                active_page="clientes",
                modo_edicao=True,
                cliente=cliente,
                dados=dados,
            )

    return render_template(
        "clientes/novo.html",
        active_page="clientes",
        modo_edicao=True,
        cliente=cliente,
        dados=_cliente_para_dict(cliente),
    )


@clientes_bp.route("/clientes/<int:id>/excluir", methods=["POST"])
def excluir_cliente(id: int):
    service = ClienteService()
    try:
        resultado = service.excluir_cliente(id)
        if resultado == "inativado":
            flash(
                "Cliente possui Ordens de Serviço vinculadas e foi inativado para preservar o histórico.",
                "success",
            )
        else:
            flash("Cliente excluído com sucesso!", "success")
    except ValueError as err:
        flash(str(err), "error")

    return redirect(url_for("clientes.listar_clientes"))


@clientes_bp.route("/clientes/cadastro-rapido", methods=["POST"])
def cadastro_rapido():
    dados = request.get_json(silent=True) or request.form.to_dict()
    service = ClienteService()

    try:
        cliente = service.cadastrar_cliente(dados)
        return (
            jsonify(
                {
                    "sucesso": True,
                    "cliente": {
                        "id": cliente.id,
                        "codigo": cliente.codigo,
                        "razao_social": cliente.razao_social,
                        "cpf_cnpj": cliente.cpf_cnpj,
                        "telefone": cliente.telefone,
                        "email": cliente.email,
                    },
                }
            ),
            201,
        )
    except ValueError as err:
        return jsonify({"sucesso": False, "erro": str(err)}), 400
