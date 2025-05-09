# routes/auth_routes.py

from flask import Blueprint, request, jsonify
from controllers.auth_controller import inscrire_utilisateur, connecter_utilisateur

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/inscription', methods=['POST'])
def inscription():
    data = request.get_json()
    return inscrire_utilisateur(data)

@auth_bp.route('/connexion', methods=['POST'])
def connexion():
    data = request.get_json()
    return connecter_utilisateur(data)
