from flask import Blueprint, render_template_string

from app.services.estoque_service import EstoqueService

estoque_bp = Blueprint("estoque", __name__)

ESTOQUE_PROVISORIO_HTML = """
{% extends "base.html" %}
{% block title %}Estoque · R.N. Soluções Industriais{% endblock %}
{% block page_header %}
<h1 class="text-xl font-bold text-gray-900">Estoque de Materiais</h1>
<p class="text-xs text-gray-500 mt-0.5">Controle de insumos e matérias-primas · Visualização provisória (Etapa 1)</p>
{% endblock %}
{% block content %}
<div class="space-y-4">
    <div class="bg-orange-50 border border-orange-200 text-orange-800 rounded-lg px-4 py-3 text-sm">
        Listagem rápida do seed carregado. A tela final do módulo de Estoque será implementada na próxima etapa.
    </div>
    <div class="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase border-b border-gray-200">
                <tr>
                    <th class="px-5 py-3">Código</th>
                    <th class="px-5 py-3">Material</th>
                    <th class="px-5 py-3">Categoria</th>
                    <th class="px-5 py-3">Saldo / Mínimo</th>
                    <th class="px-5 py-3">Custo Unit.</th>
                    <th class="px-5 py-3">Status</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                {% for item in materiais %}
                <tr class="hover:bg-gray-50">
                    <td class="px-5 py-3 font-mono text-xs text-gray-500">{{ item.codigo }}</td>
                    <td class="px-5 py-3 font-medium text-gray-900">{{ item.descricao }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ item.categoria }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ item.disponivel | int }} / {{ item.minimo | int }} {{ item.unidade }}</td>
                    <td class="px-5 py-3 text-gray-700">{{ item.custo_unitario | moeda }}</td>
                    <td class="px-5 py-3">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-medium {% if item.status_estoque == 'Normal' %}bg-emerald-50 text-emerald-700{% elif item.status_estoque == 'Baixo' %}bg-amber-50 text-amber-700{% else %}bg-red-50 text-red-700{% endif %}">
                            {{ item.status_estoque }}
                        </span>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""


@estoque_bp.route("/estoque")
def listar_estoque():
    service = EstoqueService()
    materiais = service.listar_materiais()
    return render_template_string(
        ESTOQUE_PROVISORIO_HTML,
        active_page="estoque",
        materiais=materiais,
    )

