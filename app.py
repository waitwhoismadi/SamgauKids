from flask import Flask
import os
from dotenv import load_dotenv

load_dotenv()

from config import config
from database import db

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    config[config_name].init_app(app)
    
    db.init_app(app)
    
    from email_service import email_service
    email_service.init_app(app)
    
    from routes import (auth_bp, public_bp, parent_bp, center_bp, 
                       teacher_bp, api_bp, admin_bp)
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(center_bp, url_prefix='/center')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    return app

def create_tables(app):
    with app.app_context():
        db.create_all()
        from utils import init_default_categories
        init_default_categories()

if __name__ == '__main__':
    app = create_app()
    create_tables(app)
    app.run(debug=True, host='localhost', port=5000)