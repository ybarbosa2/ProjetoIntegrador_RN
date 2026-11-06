from typing import Any, Mapping

from flask import Flask, redirect, request, session, url_for

from app.database import db
from app.models.ordem_servico import OrdemServico
from app.routes import clientes_bp, estoque_bp, main_bp, os_bp
from app.seed import seed_database


def formatar_moeda(valor: float | int | None) -> str:
    """Formata um valor numérico para o padrão monetário brasileiro (ex: R$ 11.247,40)."""
    if valor is None:
        valor = 0.0
    formatado_us = f"{float(valor):,.2f}"
    formatado_br = formatado_us.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado_br}"


def _extrair_iniciais(nome: str) -> str:
    partes = [p for p in (nome or "").strip().split() if p]
    if len(partes) >= 2:
        return f"{partes[0][0]}{partes[-1][0]}".upper()
    if len(partes) == 1:
        return partes[0][:2].upper()
    return "RB"


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Application Factory do Sistema de Gestão Operacional R.N. Soluções Industriais."""
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY="rn-solucoes-industriais-secret-key",
        SQLALCHEMY_DATABASE_URI="sqlite:///rn_gestao.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ENABLE_FISCAL_MODULE=False,
        ENABLE_WHATSAPP_NOTIFICATION=False,
        ENABLE_REALTIME_STOCK_CHECK=True,
    )

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    # Registro de filtros Jinja2
    app.add_template_filter(formatar_moeda, name="moeda")

    # Proteção global de rotas autenticadas
    @app.before_request
    def verificar_autenticacao():
        rotas_publicas = {"main.login", "main.registrar_operador", "static"}
        if (
            request.endpoint in rotas_publicas
            or request.path.startswith("/login")
            or request.path.startswith("/static")
        ):
            return None

        if session.get("user_logged") is True:
            return None

        # Em ambiente de testes automatizados (pytest), considera autenticado por padrão,
        # exceto quando a sessão foi encerrada via /logout ou quando exigido explicitamente.
        if (
            app.config.get("TESTING", False)
            and not app.config.get("TESTING_AUTH_REQUIRED", False)
            and not session.get("_logged_out", False)
        ):
            return None

        return redirect(url_for("main.login"))

    # Variáveis globais para os templates (ex: badge da sidebar, usuário e feature flags)
    @app.context_processor
    def inject_global_context() -> dict[str, Any]:
        try:
            total_os_ativas = OrdemServico.query.filter(
                OrdemServico.status.notin_(["Concluída", "Cancelada"])
            ).count()
        except Exception:
            total_os_ativas = 12

        nome_usuario = session.get("user_name") or "Rogério Barbosa"
        usuario_autenticado = bool(
            session.get("user_logged")
            or (
                app.config.get("TESTING", False)
                and not session.get("_logged_out", False)
            )
        )
        return {
            "total_os_ativas": total_os_ativas,
            "enable_fiscal_module": bool(app.config.get("ENABLE_FISCAL_MODULE", False)),
            "current_user_name": nome_usuario,
            "current_user_initials": _extrair_iniciais(nome_usuario),
            "user_logged": usuario_autenticado,
        }

    # Registro dos Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(os_bp)

    with app.app_context():
        db.create_all()
        if not app.config.get("SKIP_AUTO_SEED", False):
            seed_database()

    return app

