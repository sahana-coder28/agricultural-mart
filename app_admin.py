import os
from flask import Flask, redirect, url_for
from config import Config
from extensions import db, login_manager, bcrypt
from models import Admin
from dotenv import load_dotenv

load_dotenv()

def create_admin_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure unique session cookie name to prevent collision with user
    app.config['SESSION_COOKIE_NAME'] = 'admin_session'

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    # Unauthorized routes on admin server redirect to the admin login endpoint
    login_manager.login_view = 'admin.login'
    login_manager.login_message_category = 'info'

    @app.context_processor
    def inject_urls():
        return {
            'user_server_url': os.getenv('USER_SERVER_URL', 'http://localhost:5000'),
            'admin_server_url': os.getenv('ADMIN_SERVER_URL', 'http://localhost:5001'),
        }

    @app.route('/')
    def root_redirect():
        return redirect(url_for('admin.dashboard'))

    with app.app_context():
        # Register only the admin blueprint
        from routes.admin import admin_bp
        
        # Register blueprint with '/agromart-admin' prefix to keep paths matching the existing templates
        app.register_blueprint(admin_bp, url_prefix='/agromart-admin')
        
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_admin_app()
    port = int(os.getenv('ADMIN_PORT', 5001))
    print(f"Starting Admin Server on port {port}...")
    app.run(debug=True, port=port)
