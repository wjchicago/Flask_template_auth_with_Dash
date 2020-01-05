from flask import Blueprint

blueprint = Blueprint(
    'quote_blueprint',
    __name__,
    url_prefix='/quote',
    template_folder='templates',
    static_folder='static'
)
