from .auth import auth_bp
from .public_routes import public_bp
from .parent_routes import parent_bp
from .center_routes import center_bp
from .teacher_routes import teacher_bp
from .api_routes import api_bp
from .admin_routes import admin_bp

__all__ = [
    'auth_bp',
    'public_bp', 
    'parent_bp',
    'center_bp',
    'teacher_bp',
    'api_bp',
    'admin_bp'
]