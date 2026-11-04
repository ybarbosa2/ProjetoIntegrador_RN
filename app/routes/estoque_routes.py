from typing import Any, Dict

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.material import Material
from app.services.estoque_service import EstoqueService

estoque_bp = Blueprint("estoque", __name__)

CATEGORIAS_ESTOQUE = ["Chapas", "Tubos", "Perfis", "Consumíveis", "Barras"]


def _material_para_dict(material: Material) -> Dict[str, Any]:
    return {
        "codigo": material.codigo or "",
        "descricao": material.descricao or "",
        "subtitulo": material.subtitulo or "",
        "categoria": material.categoria or "Chapas",
        "tipo_material": material.tipo_material or "Aço carbono",
        "unidade": material.unidade or "UN",
        "disponivel": material.disponivel_formatado,
        "quantidade_inicial": material.disponivel_formatado,
        "minimo": material.minimo_formatado,
        "custo_unitario": f"{material.custo_unitario:.2f}".replace(".", ","),
        "localizacao": material.localizacao or "",
        "controle_lote": material.controle_lote or "Não utilizado",
        "fornecedor": material.fornecedor or "",
        "situacao": material.situacao or "Ativo",
        "observacoes": material.observacoes or "",
    }


@estoque_bp.route("/estoque", methods=["GET"])
def listar_estoque():
    busca = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "Todas").strip()

    if not categoria or categoria in ("Todas", "Todas as categorias", "todas"):
        categoria = "Todas"

    service = EstoqueService()
    categorias_disponiveis = service.listar_categorias_distintas()
    materiais = service.listar_materiais(busca=busca, categoria=categoria)
    indicadores = service.obter_indicadores_estoque()
    ultimas_movimentacoes = service.listar_ultimas_movimentacoes(limite=5)

    return render_template(
        "estoque/lista.html",
        active_page="estoque",
        materiais=materiais,
        busca=busca,
        categoria_atual=categoria,
        categorias=categorias_disponiveis,
        indicadores=indicadores,
        itens_baixo_estoque=indicadores["itens_baixo_estoque"],
        ultimas_movimentacoes=ultimas_movimentacoes,
    )


@estoque_bp.route("/estoque/novo", methods=["GET", "POST"])
def novo_material():
    service = EstoqueService()
    proximo_codigo = service.gerar_proximo_codigo()
    categorias_disponiveis = service.listar_categorias_distintas()
    tipos_disponiveis = service.listar_tipos_distintos()
    unidades_disponiveis = service.listar_unidades_distintas()

    if request.method == "POST":
        dados = request.form.to_dict()
        try:
            material = service.cadastrar_material(dados)
            flash(f"Material {material.codigo} cadastrado com sucesso!", "success")
            return redirect(url_for("estoque.listar_estoque"))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "estoque/novo.html",
                active_page="estoque",
                modo_edicao=False,
                material=None,
                proximo_codigo=proximo_codigo,
                categorias=categorias_disponiveis,
                tipos_material=tipos_disponiveis,
                unidades_medida=unidades_disponiveis,
                dados=dados,
            )

    return render_template(
        "estoque/novo.html",
        active_page="estoque",
        modo_edicao=False,
        material=None,
        proximo_codigo=proximo_codigo,
        categorias=categorias_disponiveis,
        tipos_material=tipos_disponiveis,
        unidades_medida=unidades_disponiveis,
        dados={
            "codigo": proximo_codigo,
            "categoria": "Chapas",
            "tipo_material": "Aço carbono",
            "unidade": "UN",
            "controle_lote": "Não utilizado",
            "fornecedor": "Aços Paulista Distribuidora",
            "situacao": "Ativo",
        },
    )


@estoque_bp.route("/estoque/<int:id>", methods=["GET"])
def detalhe_material(id: int):
    service = EstoqueService()
    material = service.buscar_por_id(id)
    if material is None:
        abort(404)

    movimentacoes = service.listar_movimentacoes_por_material(id)
    abrir_movimentacao = request.args.get("movimentar") == "1"

    return render_template(
        "estoque/detalhe.html",
        active_page="estoque",
        material=material,
        movimentacoes=movimentacoes,
        abrir_movimentacao=abrir_movimentacao,
    )


@estoque_bp.route("/estoque/<int:id>/editar", methods=["GET", "POST"])
def editar_material(id: int):
    service = EstoqueService()
    material = service.buscar_por_id(id)
    if material is None:
        abort(404)

    categorias_disponiveis = service.listar_categorias_distintas()
    tipos_disponiveis = service.listar_tipos_distintos()
    unidades_disponiveis = service.listar_unidades_distintas()

    if request.method == "POST":
        dados = request.form.to_dict()
        try:
            service.atualizar_material(id, dados)
            flash("Material atualizado com sucesso!", "success")
            return redirect(url_for("estoque.detalhe_material", id=id))
        except ValueError as err:
            flash(str(err), "error")
            return render_template(
                "estoque/novo.html",
                active_page="estoque",
                modo_edicao=True,
                material=material,
                proximo_codigo=material.codigo,
                categorias=categorias_disponiveis,
                tipos_material=tipos_disponiveis,
                unidades_medida=unidades_disponiveis,
                dados=dados,
            )

    return render_template(
        "estoque/novo.html",
        active_page="estoque",
        modo_edicao=True,
        material=material,
        proximo_codigo=material.codigo,
        categorias=categorias_disponiveis,
        tipos_material=tipos_disponiveis,
        unidades_medida=unidades_disponiveis,
        dados=_material_para_dict(material),
    )


@estoque_bp.route("/estoque/<int:id>/movimentar", methods=["POST"])
def movimentar_material(id: int):
    service = EstoqueService()
    material = service.buscar_por_id(id)
    if material is None:
        abort(404)

    tipo = (request.form.get("tipo") or "Entrada").strip()
    quantidade = request.form.get("quantidade", "")
    responsavel = (request.form.get("responsavel") or "Carlos Mendes").strip()
    descricao_movimentacao = (request.form.get("descricao_movimentacao") or "").strip()

    try:
        if tipo == "Saída":
            service.registrar_saida(
                material,
                quantidade=quantidade,
                responsavel=responsavel,
                descricao_movimentacao=descricao_movimentacao or "Consumo interno oficina",
            )
            flash("Saída de estoque registrada com sucesso!", "success")
        else:
            service.registrar_entrada(
                material,
                quantidade=quantidade,
                responsavel=responsavel,
                descricao_movimentacao=descricao_movimentacao or "Entrada de compra",
            )
            flash("Entrada de estoque registrada com sucesso!", "success")
        return redirect(url_for("estoque.detalhe_material", id=id))
    except ValueError as err:
        flash(str(err), "error")
        return redirect(url_for("estoque.detalhe_material", id=id, movimentar=1))
