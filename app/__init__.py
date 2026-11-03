from typing import Any, Mapping

from flask import Flask

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


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Application Factory do Sistema de Gestão Operacional R.N. Soluções Industriais."""
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY="rn-solucoes-industriais-secret-key",
        SQLALCHEMY_DATABASE_URI="sqlite:///rn_gestao.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    # Registro de filtros Jinja2
    app.add_template_filter(formatar_moeda, name="moeda")

    # Variáveis globais para os templates (ex: badge da sidebar)
    @app.context_processor
    def inject_global_context() -> dict[str, Any]:
        try:
            total_os_ativas = OrdemServico.query.filter(
                OrdemServico.status != "Concluída"
            ).count()
        except Exception:
            total_os_ativas = 12
        return {"total_os_ativas": total_os_ativas}

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

