import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-agromart-key'
    # Use SQLite for fallback local development, can be easily swapped to MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'agromart.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Razorpay Keys
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
    
    # Simulation mode for testing without real keys
    RAZORPAY_SIMULATE = (RAZORPAY_KEY_ID == 'your_key_id_here' or not RAZORPAY_KEY_ID)
