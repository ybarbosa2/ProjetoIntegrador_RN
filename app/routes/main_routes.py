from flask import Blueprint, render_template, render_template_string

from app.services.cliente_service import ClienteService
from app.services.estoque_service import EstoqueService
from app.services.os_service import OSService

main_bp = Blueprint("main", __name__)

CONFIGURACOES_PROVISORIO_HTML = """
{% extends "base.html" %}
{% block title %}Configurações · R.N. Soluções Industriais{% endblock %}
{% block page_header %}
<h1 class="text-xl font-bold text-gray-900">Configurações do Sistema</h1>
<p class="text-xs text-gray-500 mt-0.5">Parâmetros gerais da unidade Matriz · Sorocaba</p>
{% endblock %}
{% block content %}
<div class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm max-w-3xl">
    <div class="flex items-center gap-3 text-[#F97316] font-semibold text-sm">
        <i data-lucide="settings" class="w-5 h-5"></i>
        <span>Módulo em preparação para as próximas etapas</span>
    </div>
    <p class="text-sm text-gray-600 mt-2">
        Esta rota provisória confirma a navegação da barra lateral. Os parâmetros operacionais detalhados serão disponibilizados nas próximas iterações do MVP.
    </p>
</div>
{% endblock %}
"""


@main_bp.route("/")
def home():
    cliente_service = ClienteService()
    estoque_service = EstoqueService()
    os_service = OSService()

    return render_template(
        "home.html",
        active_page="home",
        resumo_clientes=cliente_service.obter_resumo(),
        resumo_estoque=estoque_service.obter_resumo(),
        resumo_os=os_service.obter_resumo(),
    )


@main_bp.route("/configuracoes")
def configuracoes():
    return render_template_string(
        CONFIGURACOES_PROVISORIO_HTML,
        active_page="configuracoes",
    )

