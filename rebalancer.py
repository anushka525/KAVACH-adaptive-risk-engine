from datetime import datetime

from market_data import _fetch_last_close
from models import Asset, KavachLog, db


ALLOCATION_RULES = {
    "bull": {"risky": 0.80, "safe": 0.15, "cash": 0.05},
    "volatile": {"risky": 0.40, "safe": 0.50, "cash": 0.10},
    "crash": {"risky": 0.00, "safe": 0.00, "cash": 1.00},
}

RISKY_ASSETS = ["BTC-USD", "ETH-USD"]
SAFE_ASSET = "GLD"
CASH_ASSET = "USD"


def _get_latest_prices(tickers):
    """Fetch latest prices for given tickers."""
    prices = {}
    for ticker in tickers:
        price, _ = _fetch_last_close(ticker)
        prices[ticker] = price if price is not None else 0.0
    return prices


def calculate_allocation(regime, total_value, prices):
    """
    Calculate target asset allocation based on regime.
    
    Returns dict: {symbol: quantity}
    """
    weights = ALLOCATION_RULES.get(regime, ALLOCATION_RULES["bull"])
    allocation = {}
    
    # Risky assets: split equally between BTC and ETH
    risky_value = total_value * weights["risky"]
    for asset in RISKY_ASSETS:
        if prices.get(asset, 0) > 0:
            allocation[asset] = risky_value / 2 / prices[asset]
        else:
            allocation[asset] = 0.0
    
    # Safe asset: GLD
    safe_value = total_value * weights["safe"]
    if prices.get(SAFE_ASSET, 0) > 0:
        allocation[SAFE_ASSET] = safe_value / prices[SAFE_ASSET]
    else:
        allocation[SAFE_ASSET] = 0.0
    
    # Cash: USD (store as units, 1 USD = 1 unit)
    cash_value = total_value * weights["cash"]
    allocation[CASH_ASSET] = cash_value
    
    return allocation


def deploy_capital(user, regime, portfolio_value_before=None):
    """
    Deploy user's capital based on current regime.
    Creates initial Asset rows and logs the action.
    """
    if user.deployed:
        return {"error": "User already deployed"}, 400
    
    if user.dummy_balance <= 0:
        return {"error": "No capital to deploy"}, 400
    
    portfolio_value_before = user.dummy_balance
    
    # Get latest prices
    all_tickers = RISKY_ASSETS + [SAFE_ASSET]
    prices = _get_latest_prices(all_tickers)
    
    # Calculate allocation
    allocation = calculate_allocation(regime, user.dummy_balance, prices)
    
    # Create Asset rows
    asset_types = {
        "BTC-USD": "risky",
        "ETH-USD": "risky",
        "GLD": "safe",
        "USD": "cash",
    }
    
    for symbol, quantity in allocation.items():
        if quantity > 0:
            asset = Asset(
                user_id=user.id,
                symbol=symbol,
                quantity=quantity,
                avg_price=prices.get(symbol, 1.0),
                asset_type=asset_types.get(symbol, "cash"),
            )
            db.session.add(asset)
    
    # Set dummy_balance to 0 (all deployed)
    user.dummy_balance = 0.0
    user.deployed = True
    user.last_regime = regime
    
    # Log the deployment
    portfolio_value_after = sum(
        prices.get(symbol, 1.0) * quantity for symbol, quantity in allocation.items()
    )
    
    # Calculate allocation in dollar values for frontend display
    allocation_values = {
        symbol: round(prices.get(symbol, 1.0) * quantity, 2) 
        for symbol, quantity in allocation.items()
    }
    
    log = KavachLog(
        user_id=user.id,
        action_taken="capital_deployment",
        reasoning=f"Deployed capital in {regime} regime. Target allocation: {ALLOCATION_RULES.get(regime)}",
        portfolio_value_before=portfolio_value_before,
        portfolio_value_after=portfolio_value_after,
    )
    db.session.add(log)
    db.session.commit()
    
    return {
        "message": "Capital deployed successfully",
        "regime": regime,
        "allocation": allocation_values,
        "portfolio_value": round(portfolio_value_after, 2),
    }, 201


def rebalance_portfolio(user, regime):
    """
    Rebalance user's portfolio to match target allocation for regime.
    Called when regime changes after initial deployment.
    """
    if not user.deployed:
        return {"error": "User not deployed yet"}, 400
    
    # Get current assets
    current_assets = {a.symbol: a for a in user.assets}
    
    # Calculate current portfolio value
    all_tickers = RISKY_ASSETS + [SAFE_ASSET]
    prices = _get_latest_prices(all_tickers)
    
    current_value = sum(
        prices.get(symbol, 1.0) * asset.quantity
        for symbol, asset in current_assets.items()
    )
    
    portfolio_value_before = current_value
    
    # Calculate target allocation
    allocation = calculate_allocation(regime, current_value, prices)
    
    # Update or create assets
    asset_types = {
        "BTC-USD": "risky",
        "ETH-USD": "risky",
        "GLD": "safe",
        "USD": "cash",
    }
    
    for symbol, target_quantity in allocation.items():
        if symbol in current_assets:
            current_assets[symbol].quantity = target_quantity
            current_assets[symbol].avg_price = prices.get(symbol, 1.0)
            current_assets[symbol].last_updated = datetime.utcnow()
        else:
            asset = Asset(
                user_id=user.id,
                symbol=symbol,
                quantity=target_quantity,
                avg_price=prices.get(symbol, 1.0),
                asset_type=asset_types.get(symbol, "cash"),
            )
            db.session.add(asset)
    
    # Log the rebalance
    portfolio_value_after = sum(
        prices.get(symbol, 1.0) * quantity for symbol, quantity in allocation.items()
    )
    
    # Calculate allocation in dollar values for frontend display
    allocation_values = {
        symbol: round(prices.get(symbol, 1.0) * quantity, 2)
        for symbol, quantity in allocation.items()
    }
    
    log = KavachLog(
        user_id=user.id,
        action_taken="rebalance",
        reasoning=f"Rebalanced portfolio due to regime change to {regime}. Target: {ALLOCATION_RULES.get(regime)}",
        portfolio_value_before=portfolio_value_before,
        portfolio_value_after=portfolio_value_after,
    )
    db.session.add(log)
    db.session.commit()
    
    return {
        "message": "Portfolio rebalanced successfully",
        "regime": regime,
        "allocation": allocation_values,
        "portfolio_value": round(portfolio_value_after, 2),
    }, 200
