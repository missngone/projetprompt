from flask import Blueprint, request, jsonify
from controllers.auth_controller import inscrire_utilisateur, connecter_utilisateur

auth_blueprint = Blueprint('auth_blueprint', __name__)

@auth_blueprint.route('/inscription', methods=['POST'])
def inscription():
    data = request.get_json()
    return inscrire_utilisateur(data)

@auth_blueprint.route('/connexion', methods=['POST'])
def connexion():
    data = request.get_json()
    return connecter_utilisateur(data)
