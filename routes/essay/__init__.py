from flask import Blueprint

essay_bp = Blueprint('essay', __name__, url_prefix='/essay')

from . import routes
