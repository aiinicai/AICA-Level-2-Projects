from flask import Flask, render_template
import logging
from app.utils.config_utils import load_config, get_secret_key
from app.routes.main_routes import main_bp
from app.routes.settings_routes import settings_bp
from app.routes.upload_routes import upload_bp
from app.routes.extraction_routes import extraction_bp
from app.routes.normalization_routes import normalization_bp
from app.routes.validation_routes import validation_bp
from app.routes.profile_routes import profile_bp

def create_app(config=None):
    if config is None:
        config = load_config()

    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
                
    app.config['APP_CONFIG'] = config
    app.secret_key = get_secret_key()

    # Register blueprints
    from app.routes.validation_routes import validation_bp
    from app.routes.review_routes import review_bp
    from app.routes.export_routes import export_bp
    from app.routes.ocr_routes import ocr_bp
    from app.routes.diagnostics_routes import diagnostics_bp
    from app.routes.progress_routes import progress_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(extraction_bp)
    app.register_blueprint(normalization_bp)
    app.register_blueprint(validation_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(diagnostics_bp)
    app.register_blueprint(progress_bp)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', 
                               error_title="404 Not Found", 
                               error_msg="The requested page could not be found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal Server Error: {e}", exc_info=True)
        return render_template('base.html', 
                               error_title="500 Internal Error", 
                               error_msg="An unexpected error occurred. Please check the logs."), 500

    return app
