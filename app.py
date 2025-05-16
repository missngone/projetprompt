from flask import Flask
from flask_jwt_extended import JWTManager
from routes.auth_routes import auth_blueprint
from routes.prompt_routes import prompts_blueprint



app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = ' '  # à sécuriser dans .env

jwt = JWTManager(app)

# Enregistrement des blueprints
app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(prompts_blueprint, url_prefix="/prompts")

if __name__ == "__main__":
    app.run(debug=True)
