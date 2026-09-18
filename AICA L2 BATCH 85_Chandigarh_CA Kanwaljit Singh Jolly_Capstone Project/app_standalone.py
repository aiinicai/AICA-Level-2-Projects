"""
Task Checker - Standalone Flask Application
AI-powered workflow validation system with OneDrive integration

This is the standalone application containing only Task Checker functionality.
"""

import io
import json
import logging
import os
import sys
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS

# Fix UTF-8 encoding for Windows console (allows emoji printing)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables from .env file (for local development)
load_dotenv()

# Import Task Checker blueprints
from api.agents import agents_bp
from api.checker import checker_bp
from api.checkout import checkout_bp
from api.codex_runs import codex_runs_bp
from api.human_review import human_review_bp  # Week 4
from api.tenant import tenant_bp
from api.tasks import tasks_bp

# Initialize Flask app
app = Flask(__name__)

# Disable template caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Refuse to start without an explicitly configured session-signing secret.
# A committed fallback would let an attacker forge Flask session cookies whenever
# an environment is accidentally deployed without FLASK_SECRET_KEY.
flask_secret_key = os.getenv("FLASK_SECRET_KEY")
if not flask_secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set")
app.secret_key = flask_secret_key

# ==================== CORS CONFIGURATION ====================

# Configure CORS for Task Checker frontend
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://verify.infinitysolutons.app",  # Production frontend
            os.getenv("FRONTEND_URL", "http://localhost:5500"),  # Custom frontend URL from env
            "http://localhost:5500",  # Local development
            "http://127.0.0.1:5500",  # Local development alternative
        ],
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "supports_credentials": True
    }
})

# ==================== LOGGING CONFIGURATION ====================

# Setup logging
log_dir = os.getenv("LOG_DIR", "/tmp")
log_file = os.path.join(log_dir, "task_checker.log")

# Create log directory if it doesn't exist
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # UTF-8 for log file
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== BLUEPRINT REGISTRATION ====================

# Register Task Checker API blueprints
app.register_blueprint(agents_bp, url_prefix='/api')
app.register_blueprint(checker_bp, url_prefix='/api')
app.register_blueprint(checkout_bp, url_prefix='/api')
app.register_blueprint(human_review_bp, url_prefix='/api')  # Week 4
app.register_blueprint(codex_runs_bp, url_prefix='/api')
app.register_blueprint(tenant_bp, url_prefix='/api')
app.register_blueprint(tasks_bp, url_prefix='/api')

logger.info("✅ Task Checker blueprints registered")
logger.info("   - /api/agents (Agent CRUD + User Management)")
logger.info("   - /api/agents/<id>/run-check (Check Execution)")
logger.info("   - /api/onedrive/folders (OneDrive Folder Listing)")
logger.info("   - /api/onedrive/files (OneDrive File Listing)")
logger.info("   - /api/checkout/notify (Signup Notifications)")

# ==================== OAUTH CALLBACK ENDPOINT ====================

@app.route('/onedrive/callback', methods=['GET'])
def onedrive_callback():
    """
    Handle OneDrive OAuth callback
    Exchange authorization code for refresh token

    This route is registered directly on the app (not through blueprint)
    so it's accessible at /onedrive/callback instead of /api/onedrive/callback
    """
    import requests

    try:
        # Get authorization code and state from query params
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            error_json = json.dumps(error)
            return f"""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({{
                            type: 'onedrive_error',
                            error: {error_json}
                        }}, '*');
                        window.close();
                    </script>
                </body>
            </html>
            """

        if not code or not state:
            return jsonify({'error': 'Missing code or state'}), 400

        # Validate the signed OAuth state and its age before exchanging tokens.
        from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
        try:
            state_data = URLSafeTimedSerializer(app.secret_key).loads(state, salt='onedrive-oauth', max_age=600)
        except (BadSignature, SignatureExpired):
            return jsonify({'error': 'Invalid or expired OAuth state'}), 400

        # Get OAuth credentials
        client_id = os.getenv('CLIENT_ID')
        client_secret = os.getenv('CLIENT_SECRET')
        tenant_id = os.getenv('TENANT_ID')
        redirect_uri = os.getenv('ONEDRIVE_REDIRECT_URI', 'http://localhost:5000/onedrive/callback')

        if not client_id or not client_secret or not tenant_id:
            return jsonify({'error': 'OAuth not configured'}), 500

        # Exchange code for tokens
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        token_response = requests.post(token_url, data=token_data)

        if not token_response.ok:
            error_msg = token_response.json().get('error_description', 'Token exchange failed')
            error_json = json.dumps(error_msg)
            return f"""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({{
                            type: 'onedrive_error',
                            error: {error_json}
                        }}, '*');
                        window.close();
                    </script>
                </body>
            </html>
            """

        tokens = token_response.json()
        refresh_token = tokens.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': 'No refresh token received'}), 400

        # Get user info from Microsoft Graph API
        access_token = tokens.get('access_token')
        user_info_response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'$select': 'mail,userPrincipalName'}
        )

        if not user_info_response.ok:
            raise RuntimeError('Microsoft account connected, but its email could not be read. Please try again.')

        user_info = user_info_response.json()
        account_email = user_info.get('mail') or user_info.get('userPrincipalName')
        if not account_email:
            raise RuntimeError('Microsoft did not return an email for this account. Please choose another account or contact your Microsoft 365 administrator.')

        # Return success with refresh token and email
        # Send to parent window via postMessage
        refresh_token_json = json.dumps(refresh_token)
        account_email_json = json.dumps(account_email or '')
        return f"""
        <html>
            <body>
                <h3>OneDrive Connected Successfully!</h3>
                <p>You can close this window now.</p>
                <script>
                    window.opener.postMessage({{
                        type: 'onedrive_success',
                        refreshToken: {refresh_token_json},
                        accountEmail: {account_email_json}
                    }}, '*');
                    setTimeout(() => window.close(), 2000);
                </script>
            </body>
        </html>
        """

    except Exception as e:
        print(f"Error in OneDrive callback: {str(e)}")
        error_json = json.dumps(str(e))
        return f"""
        <html>
            <body>
                <script>
                    window.opener.postMessage({{
                        type: 'onedrive_error',
                        error: {error_json}
                    }}, '*');
                    window.close();
                </script>
            </body>
        </html>
        """

logger.info("✅ OAuth callback route registered: /onedrive/callback")

# ==================== HEALTH CHECK ENDPOINT ====================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring

    Returns:
        JSON with status and version info
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Task Checker API',
        'version': '1.0.0',
        'message': 'AI-powered workflow validation system'
    }), 200

@app.route('/', methods=['GET'])
def root():
    """
    Root endpoint - serves the Task Checker frontend application
    """
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/pricing', methods=['GET'])
def pricing_page():
    """
    Pricing page - displays subscription plans
    """
    with open('pricing.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/checkout', methods=['GET'])
def checkout_page():
    """
    Checkout page - handles user signup
    """
    with open('checkout.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/api', methods=['GET'])
def api_info():
    """
    API information endpoint
    """
    return jsonify({
        'service': 'Task Checker API',
        'version': '1.0.0',
        'description': 'AI-powered workflow validation system with OneDrive integration',
        'endpoints': {
            'health': '/health',
            'agents': '/api/agents',
            'run_check': '/api/agents/<agent_id>/run-check',
            'onedrive_folders': '/api/onedrive/folders',
            'onedrive_files': '/api/onedrive/files',
            'users': '/api/users',
            'profile': '/api/auth/profile'
        },
        'documentation': 'See CLAUDE.md for architecture details'
    }), 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.path}")
    return make_response(jsonify({
        'error': 'Endpoint not found',
        'path': request.path,
        'message': 'The requested endpoint does not exist. See /health for available endpoints.'
    }), 404)

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Server Error: {str(error)}\n{traceback.format_exc()}")
    return make_response(jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please contact support if this persists.'
    }), 500)

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {str(error)}\n{traceback.format_exc()}")
    return make_response(jsonify({
        'error': 'Unexpected error',
        'message': str(error)
    }), 500)

# ==================== AFTER REQUEST HANDLER ====================

@app.after_request
def add_security_headers(response):
    """
    Add security headers to all responses
    Also handles CORS for specific origins
    """
    origin = request.headers.get('Origin')

    # Allowed origins for CORS
    allowed_origins = [
        'https://verify.infinitysolutons.app',
        os.getenv("FRONTEND_URL", "http://localhost:5500"),
        'http://localhost:5500',
        'http://127.0.0.1:5500'
    ]

    # Set CORS headers if origin is allowed
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'

    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # CORS headers
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    return response

# ==================== MAIN ====================

if __name__ == '__main__':
    """
    Run the Flask development server

    PRODUCTION NOTE:
    - For Gunicorn deployment, this section is not used
    - WSGI file directly imports 'app' object
    - Environment variables are set in WSGI file, not .env
    """

    # Get configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"🚀 Starting Task Checker API on {host}:{port}")
    logger.info(f"   Debug mode: {debug}")
    logger.info(f"   Log file: {log_file}")

    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
