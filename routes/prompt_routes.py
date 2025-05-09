from flask import Blueprint, request
from controllers.prompt_controller import ajouter_prompt
from flask_jwt_extended import jwt_required, get_jwt_identity

prompt_bp = Blueprint("prompt_bp", __name__)

@prompt_bp.route("/ajouter", methods=["POST"])
@jwt_required()
def ajouter():
    user = get_jwt_identity()
    data = request.get_json()
    return ajouter_prompt(user, data)
