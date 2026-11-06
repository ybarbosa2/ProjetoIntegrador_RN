from datetime import datetime
import math
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

STATUS_OPCOES = [
    "Em andamento",
    "Aguardando material",
    "Aberta",
    "Concluída",
    "Cancelada",
]

PERIODO_OPCOES = [
    ("sempre", "Todo o período (Sempre)"),
    ("7d", "Últimos 7 dias"),
    ("15d", "Últimos 15 dias"),
    ("30d", "Últimos 30 dias"),
    ("90d", "Últimos 90 dias"),
    ("ano", "Este ano"),
]


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


def _itens_os_para_form(ordem: OrdemServico) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    for it in ordem.itens or []:
        qtd_num = float(it.quantidade or 0.0)
        qtd_str = str(int(qtd_num)) if qtd_num.is_integer() else f"{qtd_num:.2f}".replace(".", ",")
        itens.append(
            {
                "material_id": str(it.material_id),
                "quantidade": qtd_str,
                "valor_unitario": float(it.valor_unitario or 0.0),
                "subtotal": float(it.valor_total or 0.0),
            }
        )
    return itens


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
    periodo = (request.args.get("periodo") or "sempre").strip()
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    per_page = 10

    if status not in ("Todos", *STATUS_OPCOES):
        status = "Todos"

    os_service = OsService()
    cliente_service = ClienteService()

    todas_ordens = os_service.listar_ordens(
        busca=busca,
        status=status,
        cliente_id=cliente_id,
        periodo=periodo,
    )
    clientes = cliente_service.listar_clientes(ordenar_por_nome=True)
    resumo = os_service.obter_resumo()

    total_filtrado = len(todas_ordens)
    total_pages = max(1, math.ceil(total_filtrado / per_page))
    if page > total_pages:
        page = total_pages

    inicio_idx = (page - 1) * per_page
    fim_idx = inicio_idx + per_page
    ordens_pagina = todas_ordens[inicio_idx:fim_idx]
    exibindo_inicio = (inicio_idx + 1) if total_filtrado > 0 else 0
    exibindo_fim = min(fim_idx, total_filtrado)

    return render_template(
        "os/lista.html",
        active_page="os",
        ordens=ordens_pagina,
        clientes=clientes,
        status_opcoes=STATUS_OPCOES,
        periodo_opcoes=PERIODO_OPCOES,
        busca=busca,
        status_atual=status,
        cliente_id_atual=cliente_id,
        periodo_atual=periodo,
        resumo=resumo,
        total_ordens=resumo["total"],
        total_filtrado=total_filtrado,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        exibindo_inicio=exibindo_inicio,
        exibindo_fim=exibindo_fim,
    )


@os_bp.route("/os/nova", methods=["GET", "POST"])
def nova_os():
    os_service = OsService()
    cliente_service = ClienteService()
    estoque_service = EstoqueService()

    proximo_numero = os_service.gerar_proximo_numero()
    clientes = cliente_service.listar_clientes(ordenar_por_nome=True)
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
            "prazo_entrega": "",
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

    clientes = cliente_service.listar_clientes(ordenar_por_nome=True)
    materiais = estoque_service.listar_materiais()

    if request.method == "POST":
        dados = request.form.to_dict()
        tem_secao_materiais = (
            "sincronizar_materiais" in request.form
            or "material_id[]" in request.form
            or "material_id" in request.form
        )
        lista_materiais = _extrair_materiais_formulario() if tem_secao_materiais else None
        try:
            os_service.atualizar_status_ou_dados(id, dados, lista_materiais=lista_materiais)
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
                itens_form=lista_materiais if lista_materiais is not None else _itens_os_para_form(ordem),
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
        itens_form=_itens_os_para_form(ordem),
    )


@os_bp.route("/os/<int:id>/cancelar", methods=["POST"])
def cancelar_os(id: int):
    os_service = OsService()
    ordem = os_service.buscar_por_id(id)
    if ordem is None:
        abort(404)

    try:
        os_service.cancelar_ordem_servico(id)
        flash(
            f"Ordem de Serviço #{ordem.numero} cancelada e materiais vinculados estornados ao estoque!",
            "success",
        )
    except ValueError as err:
        flash(str(err), "error")

    return redirect(url_for("os.detalhe_os", id=id))


@os_bp.route("/os/<int:id>/excluir", methods=["POST"])
def excluir_os(id: int):
    os_service = OsService()
    ordem = os_service.buscar_por_id(id)
    if ordem is None:
        abort(404)

    try:
        numero = os_service.excluir_ordem_servico(id)
        flash(
            f"Ordem de Serviço #{numero} excluída com sucesso e materiais estornados ao estoque!",
            "success",
        )
    except ValueError as err:
        flash(str(err), "error")

    return redirect(url_for("os.listar_os"))
