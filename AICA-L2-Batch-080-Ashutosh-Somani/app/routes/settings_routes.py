from flask import Blueprint, render_template, current_app

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
def settings():
    config = current_app.config['APP_CONFIG']
    
    app_settings = dict(config.items('application')) if config.has_section('application') else {}
    paths_settings = dict(config.items('paths')) if config.has_section('paths') else {}
    privacy_settings = dict(config.items('privacy')) if config.has_section('privacy') else {}
    
    return render_template('settings.html', 
                           app_settings=app_settings, 
                           paths_settings=paths_settings,
                           privacy_settings=privacy_settings)
