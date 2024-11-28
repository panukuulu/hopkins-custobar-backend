# user_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db, bcrypt  # Import db and bcrypt from app.py
from models import User  # Import User model
import json

user_bp = Blueprint('user_bp', __name__)

# User registration
@user_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "User already exists"}), 400

        # Hash password and create new user
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        return jsonify({"message": "Internal server error"}), 500

# User login
@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        # Serialize user data as a JSON string
        identity = json.dumps({"email": user.email, "user_id": user.id})
        access_token = create_access_token(identity=identity)
        return jsonify({"token": access_token}), 200
    return jsonify({"message": "Invalid credentials"}), 401

