from datetime import datetime

import yfinance as yf
import requests


DEFAULT_TICKERS = ["BTC-USD", "ETH-USD", "GLD", "TLT"]

CRYPTO_SYMBOLS = {"BTC-USD", "ETH-USD"}
STOOQ_MAP = {"GLD": "GLD.US", "TLT": "TLT.US"}
COINGECKO_MAP = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum"}


# converts a comma-separated string of tickers into a list, ensuring they are uppercase and stripped of whitespace. If the input is empty, it defaults to a predefined list of tickers.         
def parse_tickers(ticker_string):
    if not ticker_string:
        return DEFAULT_TICKERS
    return [t.strip().upper() for t in ticker_string.split(",") if t.strip()]


def _fetch_yfinance(ticker):
    """Fetch from Yahoo Finance."""
    try:
        history = yf.Ticker(ticker).history(period="5d", interval="1d")
        if history is None or history.empty:
            return None, "No data from yfinance"

        series = history["Close"].dropna()
        if series.empty:
            return None, "No price data in yfinance response"

        return float(series.iloc[-1]), None
    except Exception as e:
        return None, f"yfinance error: {str(e)}"


def _fetch_stooq(ticker):
    """Fetch from Stooq (stocks/commodities)."""
    try:
        stooq_symbol = STOOQ_MAP.get(ticker, ticker)
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        lines = response.text.strip().split("\n")
        if len(lines) < 2:
            return None, "Empty response from Stooq"
        
        parts = lines[1].split(",")
        if len(parts) < 4:
            return None, "Invalid response format from Stooq"
        
        price = float(parts[3])
        return price, None
    except Exception as e:
        return None, f"Stooq error: {str(e)}"


def _fetch_coingecko(ticker):
    """Fetch from CoinGecko (crypto)."""
    try:
        coin_id = COINGECKO_MAP.get(ticker)
        if not coin_id:
            return None, "Coin not found in CoinGecko map"
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if coin_id not in data or "usd" not in data[coin_id]:
            return None, "Coin ID not found in CoinGecko response"
        
        price = float(data[coin_id]["usd"])
        return price, None
    except Exception as e:
        return None, f"CoinGecko error: {str(e)}"


def _fetch_last_close(ticker):
    """Fetch price with fallback providers."""
    error_log = []
    
    if ticker in CRYPTO_SYMBOLS:
        # Try yfinance first, then CoinGecko
        price, err = _fetch_yfinance(ticker)
        if price is not None:
            return price, None
        error_log.append(err)
        
        price, err = _fetch_coingecko(ticker)
        if price is not None:
            return price, None
        error_log.append(err)
    else:
        # Try yfinance first, then Stooq
        price, err = _fetch_yfinance(ticker)
        if price is not None:
            return price, None
        error_log.append(err)
        
        price, err = _fetch_stooq(ticker)
        if price is not None:
            return price, None
        error_log.append(err)
    
    return None, " | ".join(error_log)


def fetch_latest_prices(tickers):
    if not tickers:
        tickers = DEFAULT_TICKERS

    prices = {}
    errors = {}
    for ticker in tickers:
        try:
            price, error = _fetch_last_close(ticker)
            prices[ticker] = price
            if error:
                errors[ticker] = error
        except Exception as exc:
            prices[ticker] = None
            errors[ticker] = f"Unexpected error: {str(exc)}"

    payload = {"timestamp": datetime.utcnow().isoformat(), "prices": prices}
    if errors:
        payload["errors"] = errors
    return payload
