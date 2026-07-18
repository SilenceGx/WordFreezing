from flask import Blueprint

math_bp = Blueprint('math', __name__, url_prefix='/math')

from . import routes
