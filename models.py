from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
# Initializes the database object to be used across the app.

# This represents the person using your financial engine.
class User(UserMixin, db.Model):   
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    dummy_balance = db.Column(db.Float, nullable=False, default=100000.0)
    deployed = db.Column(db.Boolean, nullable=False, default=False)
    last_regime = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships: Links the user to their holdings and logs.
    assets = db.relationship("Asset", backref="user", lazy=True)
    logs = db.relationship("KavachLog", backref="user", lazy=True)

# Tracks specific investments held by a user.
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    symbol = db.Column(db.String(20), nullable=False) # e.g., AAPL, BTC, GOLD
    quantity = db.Column(db.Float, nullable=False, default=0.0) # How many units of this asset the user holds
    avg_price = db.Column(db.Float, nullable=False, default=0.0) # The average price at which the user acquired this asset
    asset_type = db.Column(db.String(16), nullable=False)  # risky, safe, cash
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# The MarketState & KavachLog Models
# These store the "intelligence" and "actions" of your autonomous engine.
class MarketState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # When this market state was recorded
    regime = db.Column(db.String(16), nullable=False)  # bull, volatile, crash 
    volatility_score = db.Column(db.Float, nullable=False, default=0.0) # A numerical score representing current market volatility
    detected_by = db.Column(db.String(32), nullable=False, default="z_score") # The method used to determine the market regime (e.g., z_score, ml_model, etc.)


class KavachLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action_taken = db.Column(db.String(64), nullable=False)
    reasoning = db.Column(db.Text, nullable=False)
    portfolio_value_before = db.Column(db.Float, nullable=False, default=0.0)
    portfolio_value_after = db.Column(db.Float, nullable=False, default=0.0)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
