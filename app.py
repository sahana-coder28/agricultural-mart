from flask import Flask
from config import Config
from extensions import db, login_manager, bcrypt
from models import User, Product, CartItem, WishlistItem, Order, OrderItem

# ✅ ADD THESE 2 LINES
from dotenv import load_dotenv
import os

# ✅ LOAD ENV VARIABLES
load_dotenv()

# ✅ DEBUG (optional but recommended)
print("DEBUG GEMINI KEY:", os.getenv("GEMINI_API_KEY"))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # import routes
        from routes.auth import auth_bp
        from routes.main import main_bp
        from routes.user import user_bp
        from routes.admin import admin_bp
        from routes.chatbot import chatbot_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(admin_bp, url_prefix='/agromart-admin')
        app.register_blueprint(chatbot_bp)
        
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)