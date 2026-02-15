from datetime import datetime
from flask import Flask, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from market_data import fetch_latest_prices, parse_tickers
from models import Asset, KavachLog, MarketState, User, db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kare.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not username or not email or not password:
            return jsonify({"error": "username, email, and password are required"}), 400

        if User.query.filter((User.username == username) | (User.email == email)).first():
            return jsonify({"error": "user already exists"}), 409

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            dummy_balance=100000.0,
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "registered", "user_id": user.id}), 201

    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "invalid credentials"}), 401

        login_user(user)
        return jsonify({"message": "logged in"})

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "logged out"})

    @app.route("/me", methods=["GET"])
    @login_required
    def me():
        return jsonify(
            {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "dummy_balance": current_user.dummy_balance,
                "created_at": current_user.created_at.isoformat(),
            }
        )

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

    @app.route("/prices", methods=["GET"])
    @login_required
    def prices():
        tickers = parse_tickers(request.args.get("tickers"))
        return jsonify(fetch_latest_prices(tickers))

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
