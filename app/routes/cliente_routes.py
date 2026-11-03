from flask import Blueprint, render_template_string

from app.services.cliente_service import ClienteService

clientes_bp = Blueprint("clientes", __name__)

CLIENTES_PROVISORIO_HTML = """
{% extends "base.html" %}
{% block title %}Clientes · R.N. Soluções Industriais{% endblock %}
{% block page_header %}
<h1 class="text-xl font-bold text-gray-900">Clientes</h1>
<p class="text-xs text-gray-500 mt-0.5">Base de clientes cadastrados · Visualização provisória (Etapa 1)</p>
{% endblock %}
{% block content %}
<div class="space-y-4">
    <div class="bg-orange-50 border border-orange-200 text-orange-800 rounded-lg px-4 py-3 text-sm">
        Listagem rápida do seed carregado. A tela final do módulo de Clientes será implementada na próxima etapa.
    </div>
    <div class="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase border-b border-gray-200">
                <tr>
                    <th class="px-5 py-3">Código</th>
                    <th class="px-5 py-3">Cliente</th>
                    <th class="px-5 py-3">CPF / CNPJ</th>
                    <th class="px-5 py-3">Cidade/UF</th>
                    <th class="px-5 py-3">Situação</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                {% for cliente in clientes %}
                <tr class="hover:bg-gray-50">
                    <td class="px-5 py-3 font-mono text-xs text-gray-500">{{ cliente.codigo }}</td>
                    <td class="px-5 py-3 font-medium text-gray-900">{{ cliente.razao_social }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ cliente.cpf_cnpj }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ cliente.cidade }}/{{ cliente.estado }}</td>
                    <td class="px-5 py-3">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-medium {% if cliente.situacao == 'Ativo' %}bg-emerald-50 text-emerald-700{% else %}bg-gray-100 text-gray-600{% endif %}">
                            {{ cliente.situacao }}
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


@clientes_bp.route("/clientes")
def listar_clientes():
    service = ClienteService()
    clientes = service.listar_clientes()
    return render_template_string(
        CLIENTES_PROVISORIO_HTML,
        active_page="clientes",
        clientes=clientes,
    )

