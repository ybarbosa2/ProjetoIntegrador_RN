from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)

from app.database import db
from app.seed import seed_database
from app.services.cliente_service import ClienteService
from app.services.estoque_service import EstoqueService
from app.services.os_service import OSService

main_bp = Blueprint("main", __name__)

CREDENCIAIS_GESTOR_PADRAO = {
    "rogerio@rnsolucoes.com.br": ("admin123", "Rogério Barbosa"),
    "rogerio": ("admin123", "Rogério Barbosa"),
    "admin": ("admin123", "Rogério Barbosa"),
}

FISCAL_PREVIEW_HTML = """
{% extends "base.html" %}
{% block title %}Notas Fiscais (Experimental) · R.N. Soluções Industriais{% endblock %}
{% block page_header %}
<h1 class="text-xl font-bold text-gray-900">Módulo Fiscal e Faturamento (Experimental)</h1>
<p class="text-xs text-gray-500 mt-0.5">Funcionalidade controlada pela Feature Flag ENABLE_FISCAL_MODULE (RF06 / US05)</p>
{% endblock %}
{% block content %}
<div class="max-w-4xl bg-white border border-amber-200 rounded-xl p-6 shadow-sm space-y-4">
    <div class="inline-flex items-center gap-2 bg-amber-50 text-amber-800 text-xs font-bold px-3 py-1 rounded-full">
        <i data-lucide="flask-conical" class="w-3.5 h-3.5"></i>
        <span>ENABLE_FISCAL_MODULE = True (Ambiente Experimental)</span>
    </div>
    <h2 class="text-lg font-bold text-gray-900">Registro e Emissão de Notas Fiscais (PB05 / US05)</h2>
    <p class="text-sm text-gray-600 leading-relaxed">
        Este módulo encontra-se em evolução incremental no backlog e permanece oculto por padrão em produção através de Feature Flag, permitindo integração contínua segura na branch principal sem expor fluxos inacabados à operação da oficina.
    </p>
    <div class="pt-2">
        <a href="{{ url_for('main.configuracoes') }}"
           class="inline-flex items-center gap-2 bg-[#181B20] hover:bg-[#F97316] text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors">
            <span>Voltar para Configurações e Feature Flags</span>
        </a>
    </div>
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


@main_bp.route("/configuracoes", methods=["GET"])
def configuracoes():
    cliente_service = ClienteService()
    estoque_service = EstoqueService()
    os_service = OSService()

    resumo_clientes = cliente_service.obter_resumo()
    indicadores_estoque = estoque_service.obter_indicadores_estoque()
    resumo_os = os_service.obter_resumo()

    feature_flags = [
        {
            "chave": "ENABLE_FISCAL_MODULE",
            "titulo": "Módulo de Faturamento e Emissão de Notas Fiscais (RF06 / US05 / PB05)",
            "descricao": (
                "Controla a exibição do módulo de registro de notas fiscais na barra lateral, "
                "isolando entregas incrementais fora do escopo prioritário do MVP."
            ),
            "ativo": bool(current_app.config.get("ENABLE_FISCAL_MODULE", False)),
            "categoria_badge": "Experimental / Backlog Futuro",
            "cor_badge": "orange",
            "editavel": True,
        },
        {
            "chave": "ENABLE_WHATSAPP_NOTIFICATION",
            "titulo": "Notificação Automática de Orçamentos via WhatsApp (PB08)",
            "descricao": (
                "Disparo automatizado da proposta comercial padronizada ao telefone do cliente "
                "após geração do orçamento da O.S."
            ),
            "ativo": bool(current_app.config.get("ENABLE_WHATSAPP_NOTIFICATION", False)),
            "categoria_badge": "Backlog Futuro (Won't now)",
            "cor_badge": "gray",
            "editavel": True,
        },
        {
            "chave": "ENABLE_REALTIME_STOCK_CHECK",
            "titulo": "Validação e Bloqueio de Saldo Negativo em Tempo Real (RN02)",
            "descricao": (
                "Garante integridade física e contábil impedindo baixas manuais ou vínculos em "
                "Ordens de Serviço acima da quantidade disponível."
            ),
            "ativo": bool(current_app.config.get("ENABLE_REALTIME_STOCK_CHECK", True)),
            "categoria_badge": "Núcleo do MVP (Must)",
            "cor_badge": "emerald",
            "editavel": False,
        },
    ]

    metricas_sistema = {
        "total_clientes": resumo_clientes["total"],
        "clientes_ativos": resumo_clientes["ativos"],
        "total_materiais": indicadores_estoque["total_itens"],
        "materiais_baixo_estoque": indicadores_estoque["itens_baixo_estoque"],
        "total_movimentacoes": indicadores_estoque["total_movimentacoes"],
        "total_os": resumo_os["total"],
        "os_ativas": resumo_os["ativas"],
    }

    return render_template(
        "configuracoes.html",
        active_page="configuracoes",
        feature_flags=feature_flags,
        metricas=metricas_sistema,
    )


@main_bp.route("/configuracoes/toggle-flag", methods=["POST"])
def toggle_feature_flag():
    chave = (request.form.get("flag") or "").strip()

    if chave == "ENABLE_REALTIME_STOCK_CHECK":
        flash(
            "A flag ENABLE_REALTIME_STOCK_CHECK faz parte do núcleo obrigatório do MVP (RN02) e permanece sempre ativa.",
            "error",
        )
        return redirect(url_for("main.configuracoes"))

    if chave not in ("ENABLE_FISCAL_MODULE", "ENABLE_WHATSAPP_NOTIFICATION"):
        flash("Feature Flag desconhecida.", "error")
        return redirect(url_for("main.configuracoes"))

    novo_estado = not bool(current_app.config.get(chave, False))
    current_app.config[chave] = novo_estado
    estado_str = "Ativada (True)" if novo_estado else "Desativada (False)"
    flash(f"Feature Flag {chave} alterada para {estado_str}.", "success")
    return redirect(url_for("main.configuracoes"))


@main_bp.route("/configuracoes/reset-seed", methods=["POST"])
def reset_seed_demonstracao():
    db.drop_all()
    db.create_all()
    seed_database()
    flash(
        "Banco de dados restaurado com os dados oficiais de demonstração do protótipo Figma!",
        "success",
    )
    return redirect(url_for("main.configuracoes"))


@main_bp.route("/faturamento", methods=["GET"])
def modulo_fiscal_preview():
    if not current_app.config.get("ENABLE_FISCAL_MODULE", False):
        flash(
            "O Módulo Fiscal está desativado pela Feature Flag ENABLE_FISCAL_MODULE.",
            "error",
        )
        return redirect(url_for("main.configuracoes"))
    return render_template_string(FISCAL_PREVIEW_HTML, active_page="faturamento")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_logged") is True:
            return redirect(url_for("main.home"))
        return render_template("login.html", usuario_informado="")

    usuario_bruto = (request.form.get("usuario") or request.form.get("email") or "").strip()
    usuario_chave = usuario_bruto.lower()
    senha = (request.form.get("senha") or "").strip()

    operadores_extras = current_app.config.get("OPERADORES_CADASTRADOS", {})
    mapa_usuarios = {**CREDENCIAIS_GESTOR_PADRAO, **operadores_extras}

    credencial = mapa_usuarios.get(usuario_chave)
    if credencial is not None and credencial[0] == senha:
        nome_usuario = credencial[1]
        session.clear()
        session["user_logged"] = True
        session["user_name"] = nome_usuario
        flash(f"Bem-vindo ao sistema, {nome_usuario}!", "success")
        return redirect(url_for("main.home"))

    flash("Usuário ou senha inválidos. Verifique as credenciais informadas.", "error")
    return render_template("login.html", usuario_informado=usuario_bruto)


@main_bp.route("/login/operador", methods=["POST"])
def registrar_operador():
    nome = (request.form.get("nome") or "").strip()
    usuario = (request.form.get("usuario") or "").strip().lower()
    senha = (request.form.get("senha") or "").strip()

    if not nome or not usuario or len(senha) < 4:
        flash(
            "Informe nome completo, usuário/e-mail e uma senha de ao menos 4 caracteres.",
            "error",
        )
        return render_template("login.html", usuario_informado=usuario)

    operadores = current_app.config.setdefault("OPERADORES_CADASTRADOS", {})
    operadores[usuario] = (senha, nome)

    session.clear()
    session["user_logged"] = True
    session["user_name"] = nome
    flash(f"Operador {nome} cadastrado e autenticado com sucesso!", "success")
    return redirect(url_for("main.home"))


@main_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    if current_app.config.get("TESTING", False):
        session["_logged_out"] = True
    flash(
        "Sessão encerrada com segurança. Faça login para acessar o sistema.",
        "success",
    )
    return redirect(url_for("main.login"))
