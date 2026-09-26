from flask import Flask


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload cap

    from .routes import bp

    app.register_blueprint(bp)
    return app
