from flask import Blueprint, request
from controllers.prompt_controller import ajouter_prompt
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify

prompts_blueprint = Blueprint("prompts_blueprint", __name__)

@prompts_blueprint.route("/ajouter", methods=["POST"])
@jwt_required()
def ajouter():
    id_utilisateur = get_jwt_identity()  # Le token contient juste l'ID
    data = request.get_json()
    return ajouter_prompt(id_utilisateur, data)

@prompts_blueprint.route("/mes-prompts", methods=["GET"])
@jwt_required()
def mes_prompts():
    id_utilisateur = get_jwt_identity()

    try:
        from config import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id_prompt, titre, contenu, prix, etat, date_creation
            FROM prompts
            WHERE id_auteur = %s
            ORDER BY date_creation DESC
        """, (id_utilisateur,))

        prompts = cur.fetchall()
        cur.close()
        conn.close()

        resultats = []
        for p in prompts:
            resultats.append({
                "id_prompt": p[0],
                "titre": p[1],
                "contenu": p[2],
                "prix": p[3],
                "etat": p[4],
                "date_creation": p[5].strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(resultats), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@prompts_blueprint.route("/noter", methods=["POST"])
@jwt_required()
def noter_prompt():
    id_utilisateur = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")
    note = data.get("note")

    # Validation des champs
    if id_prompt is None or note is None:
        return jsonify({"erreur": "id_prompt et note sont requis"}), 400
    if not isinstance(note, int) or note < -10 or note > 10:
        return jsonify({"erreur": "La note doit être un entier entre -10 et +10"}), 400

    try:
        from config import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérifier que le prompt existe et qu'il n'appartient pas à l'utilisateur
        cur.execute("SELECT id_auteur FROM prompts WHERE id_prompt = %s", (id_prompt,))
        prompt = cur.fetchone()
        if not prompt:
            return jsonify({"erreur": "Prompt introuvable"}), 404
        if prompt[0] == int(id_utilisateur):
            return jsonify({"erreur": "Impossible de noter votre propre prompt"}), 403
        
        id_auteur = prompt[0]

# Récupérer le groupe de l’utilisateur connecté
        cur.execute("SELECT id_groupe FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        groupe_user = cur.fetchone()[0]

# Récupérer le groupe de l’auteur du prompt
        cur.execute("SELECT id_groupe FROM utilisateurs WHERE id_utilisateur = %s", (id_auteur,))
        groupe_auteur = cur.fetchone()[0]

# Appliquer le facteur de note
        facteur = 2 if groupe_user == groupe_auteur else 1
        note_finale = note * facteur
        cur.execute("""
    UPDATE notes SET note = %s WHERE id_prompt = %s AND id_utilisateur = %s
""", (note_finale, id_prompt, id_utilisateur))
        cur.execute("""
    INSERT INTO notes (id_prompt, id_utilisateur, note)
    VALUES (%s, %s, %s)
""", (id_prompt, id_utilisateur, note_finale))





        # Vérifier si une note existe déjà pour ce prompt par cet utilisateur
        cur.execute("""
            SELECT id_note FROM notes WHERE id_prompt = %s AND id_utilisateur = %s
        """, (id_prompt, id_utilisateur))
        existe = cur.fetchone()

        if existe:
            # Mise à jour de la note
            cur.execute("""
                UPDATE notes SET note = %s WHERE id_prompt = %s AND id_utilisateur = %s
            """, (note, id_prompt, id_utilisateur))
        else:
            # Nouvelle note
            cur.execute("""
                INSERT INTO notes (id_prompt, id_utilisateur, note)
                VALUES (%s, %s, %s)
            """, (id_prompt, id_utilisateur, note))

        # Recalcul de la note moyenne
        cur.execute("""
            SELECT AVG(note)::numeric(4,2) FROM notes WHERE id_prompt = %s
        """, (id_prompt,))
        moyenne = cur.fetchone()[0] or 0

        # Mise à jour de la note moyenne et du prix
        nouveau_prix = int(1000 * (1 + float(moyenne)))

        cur.execute("""
            UPDATE prompts SET note_moyenne = %s, prix = %s WHERE id_prompt = %s
        """, (moyenne, nouveau_prix, id_prompt))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Note enregistrée avec succès",
            "note_moyenne": float(moyenne),
            "nouveau_prix": nouveau_prix
        }), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@prompts_blueprint.route("/voter", methods=["POST"])
@jwt_required()
def voter():
    id_utilisateur = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")

    if not id_prompt:
        return jsonify({"erreur": "id_prompt requis"}), 400

    try:
        from config import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérifier si le prompt existe et n’appartient pas au user
        cur.execute("SELECT id_auteur, etat FROM prompts WHERE id_prompt = %s", (id_prompt,))
        prompt = cur.fetchone()
        if not prompt:
            return jsonify({"erreur": "Prompt introuvable"}), 404
        if prompt[0] == int(id_utilisateur):
            return jsonify({"erreur": "Impossible de voter pour votre propre prompt"}), 403
        if prompt[1] == "activé":
            return jsonify({"message": "Ce prompt est déjà activé"}), 200

        # Vérifier si ce user a déjà voté pour ce prompt
        cur.execute("SELECT id_vote FROM votes WHERE id_prompt = %s AND id_utilisateur = %s", (id_prompt, id_utilisateur))
        if cur.fetchone():
            return jsonify({"erreur": "Vous avez déjà voté pour ce prompt"}), 409

        # Récupérer le groupe du prompt et du user
        cur.execute("SELECT id_groupe FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        groupe_user = cur.fetchone()[0]

        cur.execute("SELECT id_groupe FROM utilisateurs WHERE id_utilisateur = %s", (prompt[0],))
        groupe_auteur = cur.fetchone()[0]

        poids = 2 if groupe_user == groupe_auteur else 1

        # Enregistrer le vote
        cur.execute("""
            INSERT INTO votes (id_prompt, id_utilisateur, valeur_vote)
            VALUES (%s, %s, %s)
        """, (id_prompt, id_utilisateur, poids))

        # Calcul du total des points
        cur.execute("SELECT SUM(valeur_vote) FROM votes WHERE id_prompt = %s", (id_prompt,))
        total_points = cur.fetchone()[0] or 0

        # Activer automatiquement si ≥ 6 points
        if total_points >= 6:
            cur.execute("UPDATE prompts SET etat = 'activé' WHERE id_prompt = %s", (id_prompt,))
            activation = True
        else:
            activation = False

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Vote enregistré",
            "points_actuels": total_points,
            "activé": activation
        }), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@prompts_blueprint.route("/admin/prompts", methods=["GET"])
@jwt_required()
def admin_liste_prompts():
    from config import get_db_connection
    from flask_jwt_extended import get_jwt_identity

    id_utilisateur = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérifier si c'est un admin
        cur.execute("SELECT role FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        role = cur.fetchone()[0]

        if role != "admin":
            return jsonify({"erreur": "Accès réservé à l'administrateur"}), 403

        # Récupérer tous les prompts
        cur.execute("""
            SELECT p.id_prompt, p.titre, u.nom_utilisateur, p.etat, p.note_moyenne, p.prix
            FROM prompts p
            JOIN utilisateurs u ON u.id_utilisateur = p.id_auteur
            ORDER BY p.id_prompt DESC
        """)
        prompts = cur.fetchall()

        cur.close()
        conn.close()

        resultats = []
        for p in prompts:
            resultats.append({
                "id_prompt": p[0],
                "titre": p[1],
                "auteur": p[2],
                "etat": p[3],
                "note_moyenne": float(p[4]),
                "prix": p[5]
            })

        return jsonify(resultats), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
    
#ETAT DES PROMPTS

@prompts_blueprint.route("/admin/prompts/etat", methods=["PUT"])
@jwt_required()
def changer_etat_prompt():
    from config import get_db_connection
    from flask_jwt_extended import get_jwt_identity

    id_utilisateur = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")
    nouvel_etat = data.get("etat")

    if not id_prompt or not nouvel_etat:
        return jsonify({"erreur": "id_prompt et etat sont requis"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT role FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        role = cur.fetchone()[0]

        if role != "admin":
            return jsonify({"erreur": "Accès réservé à l'administrateur"}), 403

        # Met à jour l’état
        cur.execute("UPDATE prompts SET etat = %s WHERE id_prompt = %s", (nouvel_etat, id_prompt))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": f"État du prompt {id_prompt} mis à jour à : {nouvel_etat}"}), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

#ACHETER UN PROMPT
@prompts_blueprint.route("/acheter", methods=["POST"])
@jwt_required()
def acheter_prompt():
    from config import get_db_connection
    id_utilisateur = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")

    if not id_prompt:
        return jsonify({"erreur": "id_prompt requis"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérifier que le prompt est activé
        cur.execute("""
            SELECT contenu, titre, prix, etat FROM prompts WHERE id_prompt = %s
        """, (id_prompt,))
        prompt = cur.fetchone()

        if not prompt:
            return jsonify({"erreur": "Prompt introuvable"}), 404
        if prompt[3] != "activé":
            return jsonify({"erreur": "Ce prompt n'est pas encore activé"}), 403

        # Vérifier si l'achat a déjà été fait
        cur.execute("""
            SELECT 1 FROM achats WHERE id_utilisateur = %s AND id_prompt = %s
        """, (id_utilisateur, id_prompt))
        if cur.fetchone():
            return jsonify({"message": "Vous avez déjà acheté ce prompt"}), 200

        # Enregistrer l'achat
        cur.execute("""
            INSERT INTO achats (id_utilisateur, id_prompt) VALUES (%s, %s)
        """, (id_utilisateur, id_prompt))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "titre": prompt[1],
            "contenu": prompt[0],
            "prix": prompt[2],
            "message": "Achat réussi !"
        }), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@prompts_blueprint.route("/demande-suppression", methods=["PUT"])
@jwt_required()
def demande_suppression():
    from config import get_db_connection
    id_utilisateur = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")

    if not id_prompt:
        return jsonify({"erreur": "id_prompt requis"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérifie que ce prompt appartient à l'utilisateur
        cur.execute("""
            SELECT etat FROM prompts WHERE id_prompt = %s AND id_auteur = %s
        """, (id_prompt, id_utilisateur))
        result = cur.fetchone()

        if not result:
            return jsonify({"erreur": "Prompt introuvable ou non autorisé"}), 403

        etat_actuel = result[0]

        if etat_actuel in ("à_supprimer", "supprimé"):
            return jsonify({"message": "La demande a déjà été faite"}), 200

        # Mettre à jour l'état
        cur.execute("""
            UPDATE prompts
            SET etat = 'à_supprimer'
            WHERE id_prompt = %s
        """, (id_prompt,))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Demande de suppression envoyée à l’administrateur"}), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

#demande à supprimer avec GET
@prompts_blueprint.route("/admin/prompts/a-supprimer", methods=["GET"])
@jwt_required()
def voir_demandes_suppression():
    from config import get_db_connection
    from flask_jwt_extended import get_jwt_identity

    id_utilisateur = get_jwt_identity()
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Vérifier si c'est un admin
        cur.execute("SELECT role FROM utilisateurs WHERE id_utilisateur = %s", (id_utilisateur,))
        role = cur.fetchone()[0]
        if role != "admin":
            return jsonify({"erreur": "Accès refusé"}), 403

        # Récupérer les prompts à supprimer
        cur.execute("""
            SELECT p.id_prompt, p.titre, u.nom_utilisateur, p.date_creation
            FROM prompts p
            JOIN utilisateurs u ON u.id_utilisateur = p.id_auteur
            WHERE p.etat = 'à_supprimer'
        """)
        resultats = cur.fetchall()

        cur.close()
        conn.close()

        prompts = []
        for p in resultats:
            prompts.append({
                "id_prompt": p[0],
                "titre": p[1],
                "auteur": p[2],
                "date_creation": p[3].strftime('%Y-%m-%d %H:%M')
            })

        return jsonify(prompts), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


#avec put 
@prompts_blueprint.route("/admin/prompts/traiter-suppression", methods=["PUT"])
@jwt_required()
def traiter_suppression():
    from config import get_db_connection
    from flask_jwt_extended import get_jwt_identity

    id_admin = get_jwt_identity()
    data = request.get_json()
    id_prompt = data.get("id_prompt")
    action = data.get("action")  # 'supprimer' ou 'rejeter'

    if not id_prompt or action not in ["supprimer", "rejeter"]:
        return jsonify({"erreur": "Champs id_prompt et action (supprimer|rejeter) requis"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT role FROM utilisateurs WHERE id_utilisateur = %s", (id_admin,))
        role = cur.fetchone()[0]
        if role != "admin":
            return jsonify({"erreur": "Accès refusé"}), 403

        if action == "supprimer":
            cur.execute("DELETE FROM prompts WHERE id_prompt = %s", (id_prompt,))
            message = "Prompt supprimé définitivement"
        else:
            cur.execute("UPDATE prompts SET etat = 'en_attente' WHERE id_prompt = %s", (id_prompt,))
            message = "Suppression rejetée. Le prompt revient en attente"

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": message}), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


#recherche
@prompts_blueprint.route("/recherche", methods=["GET"])
def rechercher_prompts():
    from config import get_db_connection
    mot = request.args.get("mot", "").strip().lower()

    if not mot:
        return jsonify({"erreur": "Mot-clé requis"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id_prompt, titre, SUBSTRING(contenu, 1, 100) || '...', prix
            FROM prompts
            WHERE etat = 'activé'
              AND (LOWER(titre) LIKE %s OR LOWER(contenu) LIKE %s)
            ORDER BY date_creation DESC
        """, (f"%{mot}%", f"%{mot}%"))

        resultats = cur.fetchall()
        cur.close()
        conn.close()

        prompts = []
        for p in resultats:
            prompts.append({
                "id_prompt": p[0],
                "titre": p[1],
                "aperçu": p[2],
                "prix": p[3]
            })

        return jsonify(prompts), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@prompts_blueprint.route("/mes-achats", methods=["GET"])
@jwt_required()
def mes_achats():
    from config import get_db_connection
    id_utilisateur = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT p.id_prompt, p.titre, p.contenu, p.prix, a.date_achat
            FROM achats a
            JOIN prompts p ON p.id_prompt = a.id_prompt
            WHERE a.id_utilisateur = %s
            ORDER BY a.date_achat DESC
        """, (id_utilisateur,))

        achats = cur.fetchall()
        cur.close()
        conn.close()

        resultats = []
        for a in achats:
            resultats.append({
                "id_prompt": a[0],
                "titre": a[1],
                "contenu": a[2],
                "prix": a[3],
                "date_achat": a[4].strftime('%Y-%m-%d %H:%M')
            })

        return jsonify(resultats), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@prompts_blueprint.route("/utilisateur/stats", methods=["GET"])
@jwt_required()
def stats_utilisateur():
    from config import get_db_connection
    id_utilisateur = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Nombre de prompts créés
        cur.execute("SELECT COUNT(*) FROM prompts WHERE id_auteur = %s", (id_utilisateur,))
        prompts_crees = cur.fetchone()[0]

        # Nombre d'achats
        cur.execute("SELECT COUNT(*) FROM achats WHERE id_utilisateur = %s", (id_utilisateur,))
        prompts_achetes = cur.fetchone()[0]

        # Nombre de notes
        cur.execute("SELECT COUNT(*) FROM notes WHERE id_utilisateur = %s", (id_utilisateur,))
        prompts_notes = cur.fetchone()[0]

        cur.close()
        conn.close()

        return jsonify({
            "prompts_crees": prompts_crees,
            "prompts_achetes": prompts_achetes,
            "prompts_notes": prompts_notes
        }), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


