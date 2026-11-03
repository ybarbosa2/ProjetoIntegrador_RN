from flask import Blueprint, render_template_string

from app.services.os_service import OSService

os_bp = Blueprint("os", __name__)

OS_PROVISORIO_HTML = """
{% extends "base.html" %}
{% block title %}Ordens de Serviço · R.N. Soluções Industriais{% endblock %}
{% block page_header %}
<h1 class="text-xl font-bold text-gray-900">Ordens de Serviço</h1>
<p class="text-xs text-gray-500 mt-0.5">Acompanhamento de produção e manutenção · Visualização provisória (Etapa 1)</p>
{% endblock %}
{% block content %}
<div class="space-y-4">
    <div class="bg-orange-50 border border-orange-200 text-orange-800 rounded-lg px-4 py-3 text-sm">
        Listagem rápida do seed carregado. A tela final do módulo de Ordens de Serviço será implementada na próxima etapa.
    </div>
    <div class="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase border-b border-gray-200">
                <tr>
                    <th class="px-5 py-3">Número</th>
                    <th class="px-5 py-3">Cliente</th>
                    <th class="px-5 py-3">Serviço</th>
                    <th class="px-5 py-3">Prazo</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Valor Total</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                {% for os_item in ordens %}
                <tr class="hover:bg-gray-50">
                    <td class="px-5 py-3 font-mono text-xs font-semibold text-gray-700">{{ os_item.numero }}</td>
                    <td class="px-5 py-3 font-medium text-gray-900">{{ os_item.cliente.razao_social }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ os_item.titulo_resumo }}</td>
                    <td class="px-5 py-3 text-gray-600">{{ os_item.prazo_entrega }}</td>
                    <td class="px-5 py-3">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                            {{ os_item.status }}
                        </span>
                    </td>
                    <td class="px-5 py-3 font-semibold text-gray-900">{{ os_item.valor_total | moeda }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""


@os_bp.route("/os")
def listar_os():
    service = OSService()
    ordens = service.listar_ordens()
    return render_template_string(
        OS_PROVISORIO_HTML,
        active_page="os",
        ordens=ordens,
    )

