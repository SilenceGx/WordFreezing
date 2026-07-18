from flask import Blueprint

english_bp = Blueprint('english', __name__)

from . import routes
