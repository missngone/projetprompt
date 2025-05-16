from flask import jsonify
from config import get_db_connection

def ajouter_prompt(id_utilisateur, data):
    titre = data.get("titre")
    contenu = data.get("contenu")

    if not titre or not contenu:
        return jsonify({"erreur": "Titre et contenu obligatoires"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO prompts (titre, contenu, id_auteur, prix, etat)
            VALUES (%s, %s, %s, %s, %s)
        """, (titre, contenu, id_utilisateur, 1000, 'en_attente'))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Prompt ajouté avec succès"}), 201

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
