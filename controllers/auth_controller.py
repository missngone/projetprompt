# controllers/auth_controller.py

from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from config import get_db_connection

def inscrire_utilisateur(data):
    nom = data.get("nom_utilisateur")
    email = data.get("email")
    mot_de_passe = data.get("mot_de_passe")
    role = data.get("role", "utilisateur")

    if not nom or not email or not mot_de_passe:
        return jsonify({"erreur": "Champs manquants"}), 400

    hashed_pw = generate_password_hash(mot_de_passe)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"erreur": "Email déjà utilisé"}), 409

        cur.execute("""
            INSERT INTO utilisateurs (nom_utilisateur, email, mot_de_passe, role)
            VALUES (%s, %s, %s, %s)
        """, (nom, email, hashed_pw, role))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Inscription réussie"}), 201
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

def connecter_utilisateur(data):
    email = data.get("email")
    mot_de_passe = data.get("mot_de_passe")

    if not email or not mot_de_passe:
        return jsonify({"erreur": "Champs manquants"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_utilisateur, nom_utilisateur, mot_de_passe, role FROM utilisateurs WHERE email = %s", (email,))
        utilisateur = cur.fetchone()
        cur.close()
        conn.close()

        if utilisateur and check_password_hash(utilisateur[2], mot_de_passe):
            token = create_access_token(identity=str(utilisateur[0]))  # id_utilisateur en string ✅

            return jsonify({"token": token}), 200
        else:
            return jsonify({"erreur": "Identifiants invalides"}), 401

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
