from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import get_db_connection

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/profil", methods=["GET"])
@jwt_required()
def profil():
    id_utilisateur = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT nom_utilisateur, email, role FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            return jsonify({
                "nom_utilisateur": user[0],
                "email": user[1],
                "role": user[2]
            }), 200
        else:
            return jsonify({"erreur": "Utilisateur introuvable"}), 404

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
