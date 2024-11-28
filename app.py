from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from models import db  # Import db instance from models.py
from flask_migrate import Migrate

# Initialize extensions
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()

# Application factory function
def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "supersecretkey"  # Change this in production

    # Initialize extensions with the app
    db.init_app(app)
    migrate = Migrate(app, db)

    bcrypt.init_app(app)
    jwt.init_app(app)

    # Enable CORS for all domains
    CORS(app, resources={r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }}, supports_credentials=True)

    # Register Blueprints
    from routes.user_routes import user_bp
    from routes.integration_routes import integration_bp
    from routes.calculation_routes import calculation_bp

    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(integration_bp, url_prefix='/integration')
    app.register_blueprint(calculation_bp, url_prefix='/calculation')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
