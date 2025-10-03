from flask import Blueprint

schedule_mgmt_bp = Blueprint('schedule_mgmt', __name__, url_prefix='/admin/schedule_management')

from . import routes
