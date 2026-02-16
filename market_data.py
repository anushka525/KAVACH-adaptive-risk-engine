from datetime import datetime
import time
import logging

import yfinance as yf
import requests

# Configure logging
logger = logging.getLogger(__name__)

DEFAULT_TICKERS = ["BTC-USD", "ETH-USD", "GLD", "TLT"]

CRYPTO_SYMBOLS = {"BTC-USD", "ETH-USD"}
STOOQ_MAP = {"GLD": "GLD.US", "TLT": "TLT.US"}
COINGECKO_MAP = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum"}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF = 1.5  # exponential backoff multiplier


def _retry_request(func, ticker, *args, **kwargs):
    """Retry a function call with exponential backoff."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = func(ticker, *args, **kwargs)
            return result
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                wait_time = RETRY_DELAY * (RETRY_BACKOFF ** (attempt - 1))
                logger.debug(f"Retry {attempt}/{MAX_RETRIES} for {ticker} after {wait_time}s: {str(exc)}")
                time.sleep(wait_time)
            else:
                logger.debug(f"All retries exhausted for {ticker}: {str(exc)}")
    return None


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

        price = float(series.iloc[-1])
        logger.debug(f"yfinance SUCCESS for {ticker}: ${price}")
        return price, None
    except Exception as e:
        error_msg = f"yfinance error: {str(e)}"
        logger.warning(f"Failed to get ticker '{ticker}' from yfinance reason: {error_msg}")
        return None, error_msg


def _fetch_stooq(ticker):
    """Fetch from Stooq (stocks/commodities)."""
    try:
        stooq_symbol = STOOQ_MAP.get(ticker, ticker)
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
        
        response = requests.get(url, timeout=10)  # Increased timeout
        response.raise_for_status()
        
        if not response.text or len(response.text.strip()) == 0:
            return None, "Empty response from Stooq"
        
        lines = response.text.strip().split("\n")
        if len(lines) < 2:
            return None, "Empty response from Stooq"
        
        parts = lines[1].split(",")
        if len(parts) < 4:
            return None, "Invalid response format from Stooq"
        
        price = float(parts[3])
        logger.debug(f"Stooq SUCCESS for {ticker}: ${price}")
        return price, None
    except Exception as e:
        error_msg = f"Stooq error: {str(e)}"
        logger.warning(f"Failed to get ticker '{ticker}' from Stooq reason: {error_msg}")
        return None, error_msg


def _fetch_coingecko(ticker):
    """Fetch from CoinGecko (crypto)."""
    try:
        coin_id = COINGECKO_MAP.get(ticker)
        if not coin_id:
            return None, "Coin not found in CoinGecko map"
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        
        response = requests.get(url, timeout=10)  # Increased timeout
        response.raise_for_status()
        
        data = response.json()
        if coin_id not in data or "usd" not in data[coin_id]:
            return None, "Coin ID not found in CoinGecko response"
        
        price = float(data[coin_id]["usd"])
        logger.debug(f"CoinGecko SUCCESS for {ticker}: ${price}")
        return price, None
    except Exception as e:
        error_msg = f"CoinGecko error: {str(e)}"
        logger.warning(f"Failed to get ticker '{ticker}' from CoinGecko reason: {error_msg}")
        return None, error_msg


def _fetch_last_close(ticker):
    """Fetch price with fallback providers and retry logic."""
    error_log = []
    logger.info(f"Fetching latest price for {ticker}")
    
    if ticker in CRYPTO_SYMBOLS:
        # Try yfinance first with retries, then CoinGecko
        price, err = _retry_request(_fetch_yfinance, ticker)
        if price is not None:
            logger.info(f"Successfully fetched {ticker} from yfinance (with retries)")
            return price, None
        error_log.append(err or "yfinance: unknown error")
        
        price, err = _retry_request(_fetch_coingecko, ticker)
        if price is not None:
            logger.info(f"Successfully fetched {ticker} from CoinGecko (with retries)")
            return price, None
        error_log.append(err or "CoinGecko: unknown error")
    else:
        # Try yfinance first with retries, then Stooq
        price, err = _retry_request(_fetch_yfinance, ticker)
        if price is not None:
            logger.info(f"Successfully fetched {ticker} from yfinance (with retries)")
            return price, None
        error_log.append(err or "yfinance: unknown error")
        
        price, err = _retry_request(_fetch_stooq, ticker)
        if price is not None:
            logger.info(f"Successfully fetched {ticker} from Stooq (with retries)")
            return price, None
        error_log.append(err or "Stooq: unknown error")
    
    logger.error(f"All providers failed for {ticker}. Errors: {' | '.join(error_log)}")
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
