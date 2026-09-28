import os
from flask import Flask
from config import Config
from extensions import db, login_manager, bcrypt
from models import User
from dotenv import load_dotenv

load_dotenv()

def create_user_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure unique session cookie name to prevent collision with admin
    app.config['SESSION_COOKIE_NAME'] = 'user_session'

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @app.context_processor
    def inject_urls():
        return {
            'user_server_url': os.getenv('USER_SERVER_URL', 'http://localhost:5000'),
            'admin_server_url': os.getenv('ADMIN_SERVER_URL', 'http://localhost:5001'),
        }

    with app.app_context():
        # Register user/customer/farmer blueprints only
        from routes.auth import auth_bp
        from routes.main import main_bp
        from routes.user import user_bp
        from routes.chatbot import chatbot_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(chatbot_bp)
        
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_user_app()
    port = int(os.getenv('USER_PORT', 5000))
    print(f"Starting User Server on port {port}...")
    app.run(debug=True, port=port)
