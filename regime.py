from datetime import datetime
import io
import time
import logging

import pandas as pd
import requests
import yfinance as yf

# Configure logging
logger = logging.getLogger(__name__)

RISKY_TICKER = "BTC-USD"
SAFE_TICKER = "GLD"

VOL_WINDOW = 30
Z_WINDOW = 90
LEVEL2_Z = 2.0
LEVEL3_Z = 3.0
RISKY_DROP_7D = -0.05
SAFE_DROP_7D = -0.02

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


def _history_yfinance(ticker, period="220d"):
    try:
        history = yf.Ticker(ticker).history(period=period, interval="1d")
        if history is None or history.empty:
            return None, "No data from yfinance"

        series = history["Close"].dropna()
        if series.empty:
            return None, "No price data in yfinance response"

        logger.debug(f"yfinance SUCCESS for {ticker}: {len(series)} days")
        return series, None
    except Exception as exc:
        error_msg = f"yfinance error: {str(exc)}"
        logger.warning(f"Failed to get ticker '{ticker}' from yfinance: {error_msg}")
        return None, error_msg


def _history_stooq(ticker):
    try:
        stooq_symbol = STOOQ_MAP.get(ticker, ticker)
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
        response = requests.get(url, timeout=10)  # Increased timeout
        response.raise_for_status()

        if not response.text or len(response.text.strip()) == 0:
            return None, "Empty response from Stooq"

        data = pd.read_csv(io.StringIO(response.text))
        if "Date" not in data.columns:
            return None, "Missing Date column in Stooq response"

        close_col = "Close" if "Close" in data.columns else "close"
        if close_col not in data.columns:
            return None, "Missing Close column in Stooq response"

        data["Date"] = pd.to_datetime(data["Date"])
        series = pd.to_numeric(data[close_col], errors="coerce")
        series.index = data["Date"]
        series = series.dropna()

        if series.empty:
            return None, "No price data in Stooq response"

        logger.debug(f"Stooq SUCCESS for {ticker}: {len(series)} days")
        return series, None
    except Exception as exc:
        error_msg = f"Stooq error: {str(exc)}"
        logger.warning(f"Failed to get ticker '{ticker}' from Stooq: {error_msg}")
        return None, error_msg


def _history_coingecko(ticker, days=220):
    try:
        coin_id = COINGECKO_MAP.get(ticker)
        if not coin_id:
            return None, "Coin not found in CoinGecko map"

        url = (
            "https://api.coingecko.com/api/v3/coins/"
            f"{coin_id}/market_chart?vs_currency=usd&days={days}"
        )
        response = requests.get(url, timeout=10)  # Increased timeout
        response.raise_for_status()

        data = response.json()
        prices = data.get("prices")
        if not prices:
            return None, "No prices in CoinGecko response"

        frame = pd.DataFrame(prices, columns=["ts", "price"])
        frame["date"] = pd.to_datetime(frame["ts"], unit="ms").dt.date
        series = frame.groupby("date")["price"].last()
        series.index = pd.to_datetime(series.index)
        series = series.dropna()

        if series.empty:
            return None, "No price data in CoinGecko response"

        logger.debug(f"CoinGecko SUCCESS for {ticker}: {len(series)} days")
        return series, None
    except Exception as exc:
        error_msg = f"CoinGecko error: {str(exc)}"
        logger.warning(f"Failed to get ticker '{ticker}' from CoinGecko: {error_msg}")
        return None, error_msg


def _fetch_history(ticker):
    """Fetch history with retry logic and multiple fallback providers."""
    error_log = []
    logger.info(f"Fetching history for {ticker}")

    if ticker in CRYPTO_SYMBOLS:
        # Try yfinance with retries
        series, err = _retry_request(_history_yfinance, ticker)
        if series is not None:
            logger.info(f"Successfully fetched {ticker} from yfinance (with retries)")
            return series, None
        error_log.append(err or "yfinance: unknown error")

        # Try CoinGecko with retries
        series, err = _retry_request(_history_coingecko, ticker)
        if series is not None:
            logger.info(f"Successfully fetched {ticker} from CoinGecko (with retries)")
            return series, None
        error_log.append(err or "CoinGecko: unknown error")
    else:
        # Try yfinance with retries
        series, err = _retry_request(_history_yfinance, ticker)
        if series is not None:
            logger.info(f"Successfully fetched {ticker} from yfinance (with retries)")
            return series, None
        error_log.append(err or "yfinance: unknown error")

        # Try Stooq with retries
        series, err = _retry_request(_history_stooq, ticker)
        if series is not None:
            logger.info(f"Successfully fetched {ticker} from Stooq (with retries)")
            return series, None
        error_log.append(err or "Stooq: unknown error")

    logger.error(f"All providers failed for {ticker}. Errors: {' | '.join(error_log)}")
    return None, " | ".join(error_log)


def _seven_day_return(series):
    if series is None or len(series) < 8:
        return None

    latest = series.iloc[-1]
    previous = series.iloc[-8]
    if previous == 0:
        return None

    return (latest / previous) - 1


def _rolling_vol_zscore(returns):
    rolling_vol = returns.rolling(VOL_WINDOW).std().dropna()
    if rolling_vol.empty:
        return None, None, None

    current_vol = float(rolling_vol.iloc[-1])
    window = rolling_vol.tail(Z_WINDOW)
    mean_vol = float(window.mean())
    std_vol = float(window.std()) if float(window.std()) > 0 else None

    if std_vol is None:
        return current_vol, mean_vol, None

    z_score = (current_vol - mean_vol) / std_vol
    return current_vol, mean_vol, float(z_score)


def detect_regime(risky_ticker=RISKY_TICKER, safe_ticker=SAFE_TICKER):
    errors = {}
    detected_by = "z_score"

    risky_series, err = _fetch_history(risky_ticker)
    if err:
        errors[risky_ticker] = err

    safe_series, err = _fetch_history(safe_ticker)
    if err:
        errors[safe_ticker] = err

    if risky_series is None:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": 1,
            "regime": "bull",
            "reasoning": ["Insufficient risky asset history"],
            "metrics": {},
            "errors": errors,
            "detected_by": "fallback",
        }

    returns = risky_series.pct_change().dropna()
    current_vol, mean_vol, z_score = _rolling_vol_zscore(returns)
    price = float(risky_series.iloc[-1])

    ma200 = None
    if len(risky_series) >= 200:
        ma200 = float(risky_series.rolling(200).mean().iloc[-1])

    risky_7d = _seven_day_return(risky_series)
    safe_7d = _seven_day_return(safe_series) if safe_series is not None else None

    risky_drop = risky_7d is not None and risky_7d <= RISKY_DROP_7D
    safe_drop = safe_7d is not None and safe_7d <= SAFE_DROP_7D

    reasoning = []
    if z_score is None:
        reasoning.append("Insufficient data for volatility z-score")
    else:
        reasoning.append(f"Volatility z-score: {z_score:.2f}")

    if risky_drop:
        reasoning.append(f"Risky 7d return: {risky_7d:.2%}")
    if safe_drop:
        reasoning.append(f"Safe 7d return: {safe_7d:.2%}")

    level = 1
    regime = "bull"

    if (z_score is not None and z_score >= LEVEL3_Z) or (risky_drop and safe_drop):
        level = 3
        regime = "crash"
        detected_by = "z_score_or_safe_breakdown"
        reasoning.append("Level 3 triggered")
    elif z_score is not None and z_score >= LEVEL2_Z:
        level = 2
        regime = "volatile"
        detected_by = "z_score"
        reasoning.append("Level 2 triggered")
    else:
        reasoning.append("Level 1 triggered")

    metrics = {
        "price": price,
        "current_vol": current_vol,
        "mean_vol": mean_vol,
        "z_score": z_score,
        "ma200": ma200,
        "risky_7d": risky_7d,
        "safe_7d": safe_7d,
    }

    response = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "regime": regime,
        "reasoning": reasoning,
        "metrics": metrics,
        "detected_by": detected_by,
    }

    if errors:
        response["errors"] = errors

    return response
