from dotenv import load_dotenv
import os

load_dotenv()

from datetime import datetime
import logging
from flask import Flask, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from market_data import fetch_latest_prices, parse_tickers
from regime import detect_regime
from rebalancer import deploy_capital, rebalance_portfolio
from models import Asset, KavachLog, MarketState, User, db


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kare.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Enable CORS for frontend communication
    CORS(app, resources={r"/*": {"origins": ["https://kavach-adaptive-risk-engine.netlify.app", "http://localhost:5173"], "supports_credentials": True}})

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
                "deployed": current_user.deployed,
                "last_regime": current_user.last_regime,
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

    @app.route("/regime", methods=["GET"])
    @login_required
    def regime():
        risky = request.args.get("risky") or None
        safe = request.args.get("safe") or None
        logger.info(f"Detecting regime for user {current_user.username}")
        result = detect_regime(risky_ticker=risky or "BTC-USD", safe_ticker=safe or "GLD")
        logger.info(f"Regime detection result: Level {result['level']} ({result['regime']}), detected_by: {result.get('detected_by')}")

        rebalance_result = None
        if current_user.deployed:
            last_regime = current_user.last_regime
            if last_regime and last_regime != result["regime"]:
                logger.info(f"Regime changed from {last_regime} to {result['regime']} - triggering rebalance")
                rebalance_result, _ = rebalance_portfolio(current_user, result["regime"])
        current_user.last_regime = result["regime"]

        state = MarketState(
            regime=result["regime"],
            volatility_score=float(result.get("metrics", {}).get("z_score") or 0.0),
            detected_by=result.get("detected_by", "z_score"),
        )
        db.session.add(state)
        if rebalance_result:
            result["rebalance"] = rebalance_result
        db.session.commit()

        return jsonify(result)

    @app.route("/deploy", methods=["POST"])
    @login_required
    def deploy():
        # Step 1: Detect current regime
        regime_result = detect_regime()
        regime = regime_result.get("regime", "bull")
        
        # Step 2: Deploy capital based on regime
        response, status_code = deploy_capital(current_user, regime)
        
        return jsonify(response), status_code

    @app.route("/stress-test", methods=["POST"])
    @login_required
    def stress_test():
        """Test rebalancing by simulating a market crash (Level 3 regime)."""
        if not current_user.deployed:
            return jsonify({"error": "portfolio not deployed yet. call /deploy first"}), 400
        
        # Get current real regime for context
        real_result = detect_regime()
        real_regime = real_result.get("regime", "bull")
        previous_regime = current_user.last_regime or "unknown"
        
        # Simulate a crash
        rebalance_result, status_code = rebalance_portfolio(current_user, "crash")
        
        # Get the most recent log entry for details
        latest_log = KavachLog.query.filter_by(user_id=current_user.id).order_by(KavachLog.timestamp.desc()).first()
        
        return jsonify({
            "status": "stress test executed",
            "test_scenario": "simulated market crash (Level 3)",
            "previous_regime": previous_regime,
            "real_detected_regime": real_regime,
            "simulated_regime": "crash",
            "rebalance_triggered": status_code == 200,
            "rebalance_details": rebalance_result,
            "latest_log": {
                "action": latest_log.action_taken if latest_log else None,
                "reasoning": latest_log.reasoning if latest_log else None,
                "portfolio_value_before": latest_log.portfolio_value_before if latest_log else None,
                "portfolio_value_after": latest_log.portfolio_value_after if latest_log else None,
                "timestamp": latest_log.timestamp.isoformat() if latest_log else None,
            },
            "note": "Real market regime is still stored as '{}'—this test doesn't affect autopilot".format(real_regime)
        }), 200

    return app


app = create_app()

# Create database tables (works with both gunicorn and direct python execution)
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
