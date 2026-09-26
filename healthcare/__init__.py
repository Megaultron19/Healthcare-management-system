import os

from flask import Flask, render_template

from .extensions import csrf, db, login_manager
from .utils import local_today

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _database_url():
    """Neon/Vercel expose DATABASE_URL (or POSTGRES_URL). Fall back to a local SQLite file."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        if os.environ.get("VERCEL"):
            raise RuntimeError("DATABASE_URL must be set in production (connect a Neon database in Vercel → Storage).")
        os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
        return "sqlite:///" + os.path.join(BASE_DIR, "instance", "healthcare.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        # Served by Flask locally and by Vercel's CDN (public/**) in production.
        static_folder=os.path.join(BASE_DIR, "public", "static"),
        static_url_path="/static",
    )

    on_vercel = bool(os.environ.get("VERCEL"))
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if on_vercel:
            raise RuntimeError("SECRET_KEY environment variable must be set in production.")
        secret_key = "dev-only-insecure-key"

    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=_database_url(),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_vercel,
        REMEMBER_COOKIE_SECURE=on_vercel,
        APP_NAME=os.environ.get("APP_NAME", "Clinic Manager"),
        PER_PAGE=15,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (register tables)
    from .appointments import bp as appointments_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .doctors import bp as doctors_bp
    from .patients import bp as patients_bp
    from .records import bp as records_bp

    for bp in (auth_bp, dashboard_bp, patients_bp, doctors_bp, appointments_bp, records_bp):
        app.register_blueprint(bp)

    from .cli import register_cli

    register_cli(app)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_globals():
        return {"app_name": app.config["APP_NAME"], "today": local_today()}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="You don't have permission to do that."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="The page you're looking for doesn't exist."), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

    return app
