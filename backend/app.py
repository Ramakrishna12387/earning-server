import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from .database import db
from .config import DATABASE_URL
from .routes import api


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend"
)


def create_app():

    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path="/static"
    )

    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    db.init_app(app)

    # API routes
    app.register_blueprint(
        api,
        url_prefix="/api"
    )

    # -----------------------------------------
    # Frontend
    # -----------------------------------------

    @app.route("/")
    def home():

        return send_from_directory(
            FRONTEND_DIR,
            "index.html"
        )

    @app.route("/css/<path:filename>")
    def css_files(filename):

        return send_from_directory(
            os.path.join(
                FRONTEND_DIR,
                "css"
            ),
            filename
        )

    @app.route("/js/<path:filename>")
    def js_files(filename):

        return send_from_directory(
            os.path.join(
                FRONTEND_DIR,
                "js"
            ),
            filename
        )

    # -----------------------------------------
    # Health check
    # -----------------------------------------

    @app.route("/health")
    def health():

        return {
            "status": "ok",
            "app": "White Jack",
            "message": "Server is running"
        }

    # -----------------------------------------
    # Database
    # -----------------------------------------

    with app.app_context():

        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )