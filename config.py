# config.py

import psycopg2

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="gestion_prompts",
        user="postgres",  # remplace par ton utilisateur PostgreSQL
        password="2211",  # remplace par ton mot de passe PostgreSQL
        port="5432"
    )
