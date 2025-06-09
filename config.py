import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///education_platform.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    
    MAIL_SUBJECT_PREFIX = '[EduPlatform] '
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or os.environ.get('MAIL_USERNAME')
    
    RESET_PASSWORD_SALT = os.environ.get('RESET_PASSWORD_SALT') or 'reset-password-salt'
    RESET_TOKEN_EXPIRATION = 3600 
    
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'
    
    @staticmethod
    def init_app(app):
        if app.debug:
            print(f"📧 Email Configuration:")
            print(f"   MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
            print(f"   MAIL_PORT: {app.config.get('MAIL_PORT')}")
            print(f"   MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
            print(f"   MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
            print(f"   MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}