from flask import Flask
from flask_jwt_extended import JWTManager
from routes.auth_routes import auth_bp
from routes.prompt_routes import prompt_bp



app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = ' '  # à mettre dans .env plus tard

app.register_blueprint(prompt_bp, url_prefix="/prompts")

jwt = JWTManager(app)

# Enregistrement des routes
app.register_blueprint(auth_bp, url_prefix="/auth")

if __name__ == "__main__":
    app.run(debug=True)
