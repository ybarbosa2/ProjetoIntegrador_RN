from datetime import datetime, timedelta
from typing import Any, Dict, List

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.ordem_servico import OrdemServico
from app.services.cliente_service import ClienteService
from app.services.estoque_service import EstoqueService
from app.services.os_service import OsService

os_bp = Blueprint("os", __name__)

STATUS_OPCOES = ["Em andamento", "Aguardando material", "Aberta", "Concluída"]


def _os_para_dict(ordem: OrdemServico) -> Dict[str, Any]:
    return {
        "numero": ordem.numero or "",
        "cliente_id": str(ordem.cliente_id or ""),
        "data_abertura": ordem.data_abertura or "",
        "prazo_entrega": ordem.prazo_entrega or "",
        "status": ordem.status or "Aberta",
        "titulo_resumo": ordem.titulo_resumo or "",
        "tipo_servico": ordem.tipo_servico or "Fabricação de estrutura metálica",
        "quantidade_servico": ordem.quantidade_servico or "1 conjunto",
        "responsavel": ordem.responsavel or "Carlos Mendes",
        "descricao_detalhada": ordem.descricao_detalhada or "",
        "especificacoes_tecnicas": ordem.especificacoes_tecnicas or "",
        "valor_mao_de_obra": f"{float(ordem.valor_mao_de_obra or 0.0):.2f}".replace(".", ","),
    }


def _extrair_materiais_formulario() -> List[Dict[str, Any]]:
    mat_ids = request.form.getlist("material_id[]") or request.form.getlist("material_id")
    mat_qtds = (
        request.form.getlist("material_quantidade[]")
        or request.form.getlist("material_quantidade")
        or request.form.getlist("quantidade[]")
        or request.form.getlist("quantidade")
    )
    itens: List[Dict[str, Any]] = []
    for mid, qtd in zip(mat_ids, mat_qtds):
        if str(mid).strip() != "" and str(qtd).strip() != "":
            itens.append({"material_id": str(mid).strip(), "quantidade": str(qtd).strip()})
    return itens


@os_bp.route("/os", methods=["GET"])
def listar_os():
    busca = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "Todos").strip()
    cliente_id = (request.args.get("cliente_id") or "Todos").strip()

    if status not in ("Todos", *STATUS_OPCOES):
        status = "Todos"

    os_service = OsService()
    cliente_service = ClienteService()

    ordens = os_service.listar_ordens(busca=busca, status=status, cliente_id=cliente_id)
    clientes = cliente_service.listar_clientes()
    resumo = os_service.obter_resumo()

    return render_template(
        "os/lista.html",
        active_page="os",
        ordens=ordens,
        clientes=clientes,
        status_opcoes=STATUS_OPCOES,
        busca=busca,
        status_atual=status,
        cliente_id_atual=cliente_id,
        resumo=resumo,
        total_ordens=resumo["total"],
    )


@os_bp.route("/os/nova", methods=["GET", "POST"])
def nova_os():
    os_service = OsService()
    cliente_service = ClienteService()
    estoque_service = EstoqueService()

    proximo_numero = os_service.gerar_proximo_numero()
    clientes = cliente_service.listar_clientes()
    materiais = estoque_service.listar_materiais()

    if request.method == "POST":
        dados = request.form.to_dict()
        lista_materiais = _extrair_materiais_formulario()
        try:
            nova = os_service.criar_ordem_servico(dados, lista_materiais=lista_materiais)
            flash(f"Ordem de Serviço #{nova.numero} criada com sucesso!", "success")
            return redirect(url_for("os.detalhe_os", id=nova.id))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "os/nova.html",
                active_page="os",
                modo_edicao=False,
                ordem=None,
                proximo_numero=proximo_numero,
                clientes=clientes,
                materiais=materiais,
                status_opcoes=STATUS_OPCOES,
                dados=dados,
                itens_form=lista_materiais,
            )

    hoje = datetime.now()
    cliente_pre_selecionado = (request.args.get("cliente_id") or "").strip()

    return render_template(
        "os/nova.html",
        active_page="os",
        modo_edicao=False,
        ordem=None,
        proximo_numero=proximo_numero,
        clientes=clientes,
        materiais=materiais,
        status_opcoes=STATUS_OPCOES,
        dados={
            "numero": proximo_numero,
            "cliente_id": cliente_pre_selecionado,
            "data_abertura": hoje.strftime("%d/%m/%Y"),
            "prazo_entrega": (hoje + timedelta(days=15)).strftime("%d/%m/%Y"),
            "status": "Aberta",
            "tipo_servico": "Fabricação de estrutura metálica",
            "quantidade_servico": "1 conjunto",
            "responsavel": "Carlos Mendes",
            "valor_mao_de_obra": "0,00",
        },
        itens_form=[],
    )


@os_bp.route("/os/<int:id>", methods=["GET"])
def detalhe_os(id: int):
    os_service = OsService()
    ordem = os_service.buscar_por_id(id)
    if ordem is None:
        abort(404)

    orcamento = os_service.gerar_orcamento(ordem)
    abrir_orcamento = request.args.get("orcamento") == "1"

    return render_template(
        "os/detalhe.html",
        active_page="os",
        os=ordem,
        orcamento=orcamento,
        status_opcoes=STATUS_OPCOES,
        abrir_orcamento=abrir_orcamento,
    )


@os_bp.route("/os/<int:id>/editar", methods=["GET", "POST"])
def editar_os(id: int):
    os_service = OsService()
    cliente_service = ClienteService()
    estoque_service = EstoqueService()

    ordem = os_service.buscar_por_id(id)
    if ordem is None:
        abort(404)

    clientes = cliente_service.listar_clientes()
    materiais = estoque_service.listar_materiais()

    if request.method == "POST":
        dados = request.form.to_dict()
        try:
            os_service.atualizar_status_ou_dados(id, dados)
            flash(f"Ordem de Serviço #{ordem.numero} atualizada com sucesso!", "success")
            return redirect(url_for("os.detalhe_os", id=id))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "os/nova.html",
                active_page="os",
                modo_edicao=True,
                ordem=ordem,
                proximo_numero=ordem.numero,
                clientes=clientes,
                materiais=materiais,
                status_opcoes=STATUS_OPCOES,
                dados=dados,
                itens_form=[],
            )

    return render_template(
        "os/nova.html",
        active_page="os",
        modo_edicao=True,
        ordem=ordem,
        proximo_numero=ordem.numero,
        clientes=clientes,
        materiais=materiais,
        status_opcoes=STATUS_OPCOES,
        dados=_os_para_dict(ordem),
        itens_form=[],
    )
