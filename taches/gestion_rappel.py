import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import get_db_connection
from datetime import datetime, timedelta

def mettre_en_rappel():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        limite_24h = datetime.now() - timedelta(hours=24)
        limite_48h = datetime.now() - timedelta(hours=48)

        # prompts en attente de suppression depuis > 24h
        cur.execute("""
            UPDATE prompts
            SET etat = 'rappel'
            WHERE etat = 'à_supprimer' AND date_modification < %s
        """, (limite_24h,))

        # prompts à revoir depuis > 48h
        cur.execute("""
            UPDATE prompts
            SET etat = 'rappel'
            WHERE etat = 'à_revoir' AND date_modification < %s
        """, (limite_48h,))

        conn.commit()
        cur.close()
        conn.close()

        print("Prompts mis à jour avec l'état 'rappel' si nécessaire.")

    except Exception as e:
        print("Erreur :", e)

if __name__ == "__main__":
    mettre_en_rappel()
