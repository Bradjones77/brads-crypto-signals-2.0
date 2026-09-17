import os
import time
import hmac
import base64
import hashlib
import json
from typing import Dict, List, Optional, Any

import requests


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# BITGET MARKET DATA ENGINE
#
# READ-ONLY MARKET DATA.
# THIS FILE DOES NOT PLACE TRADES.
# ============================================================


BITGET_BASE_URL = (
    os.getenv(
        "SIGNALS2_BITGET_BASE_URL",
        "https://api.bitget.com",
    )
    or ""
).strip().rstrip("/")


BITGET_API_KEY = (
    os.getenv("SIGNALS2_BITGET_API_KEY")
    or ""
).strip()

BITGET_API_SECRET = (
    os.getenv("SIGNALS2_BITGET_API_SECRET")
    or ""
).strip()

BITGET_PASSPHRASE = (
    os.getenv("SIGNALS2_BITGET_PASSPHRASE")
    or ""
).strip()


PRODUCT_TYPE = "USDT-FUTURES"

REQUEST_TIMEOUT = int(
    os.getenv(
        "SIGNALS2_BITGET_TIMEOUT",
        "15",
    )
)

MAX_RETRIES = int(
    os.getenv(
        "SIGNALS2_BITGET_MAX_RETRIES",
        "4",
    )
)


# ============================================================
# SESSION
# ============================================================


SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
        "brads-signals-bot-2.0",
        "Accept":
        "application/json",
        "Content-Type":
        "application/json",
    }
)


# ============================================================
# READ-ONLY SAFETY
# ============================================================


def _assert_read_only_method(
    method: str,
):
    """
    Hard safety barrier.

    This market-data module only permits GET requests.

    If code accidentally attempts POST, PUT,
    PATCH or DELETE through this module,
    it is rejected before reaching Bitget.
    """

    method = str(method).upper().strip()

    if method != "GET":
        raise RuntimeError(
            "READ-ONLY SAFETY BLOCK: "
            f"{method} requests are not permitted "
            "by bitget_market.py"
        )


# ============================================================
# AUTHENTICATION
# ============================================================


def private_credentials_available() -> bool:
    return bool(
        BITGET_API_KEY
        and BITGET_API_SECRET
        and BITGET_PASSPHRASE
    )


def _timestamp_ms() -> str:
    return str(
        int(time.time() * 1000)
    )


def _build_query_string(
    params: Optional[Dict[str, Any]],
) -> str:

    if not params:
        return ""

    items = []

    for key in sorted(params.keys()):
        value = params[key]

        if value is None:
            continue

        items.append(
            f"{key}={value}"
        )

    return "&".join(items)


def _sign(
    timestamp: str,
    method: str,
    request_path: str,
    query_string: str = "",
    body: str = "",
) -> str:

    if not private_credentials_available():
        raise RuntimeError(
            "Signals Bot 2.0 Bitget credentials "
            "are not configured."
        )

    method = method.upper()

    path_with_query = request_path

    if query_string:
        path_with_query += (
            "?"
            + query_string
        )

    message = (
        timestamp
        + method
        + path_with_query
        + body
    )

    digest = hmac.new(
        BITGET_API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(
        digest
    ).decode("utf-8")


def _private_headers(
    method: str,
    request_path: str,
    params: Optional[Dict[str, Any]] = None,
    body: str = "",
) -> Dict[str, str]:

    timestamp = _timestamp_ms()

    query_string = _build_query_string(
        params
    )

    signature = _sign(
        timestamp=timestamp,
        method=method,
        request_path=request_path,
        query_string=query_string,
        body=body,
    )

    return {
        "ACCESS-KEY":
        BITGET_API_KEY,

        "ACCESS-SIGN":
        signature,

        "ACCESS-TIMESTAMP":
        timestamp,

        "ACCESS-PASSPHRASE":
        BITGET_PASSPHRASE,

        "Content-Type":
        "application/json",

        "locale":
        "en-US",
    }


# ============================================================
# SAFE HTTP
# ============================================================


def _request(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    private: bool = False,
) -> Any:

    _assert_read_only_method(
        "GET"
    )

    url = (
        BITGET_BASE_URL
        + path
    )

    delay = 1.0
    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            headers = {}

            if private:
                headers = _private_headers(
                    method="GET",
                    request_path=path,
                    params=params,
                )

            response = SESSION.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                try:
                    retry_after = float(
                        retry_after
                    )
                except Exception:
                    retry_after = delay

                time.sleep(
                    max(
                        delay,
                        retry_after,
                    )
                )

                delay = min(
                    delay * 2,
                    30,
                )

                continue

            if (
                response.status_code
                >= 500
            ):
                raise RuntimeError(
                    "Bitget server error "
                    f"{response.status_code}"
                )

            response.raise_for_status()

            payload = response.json()

            if not isinstance(
                payload,
                dict,
            ):
                raise RuntimeError(
                    "Unexpected Bitget response."
                )

            code = str(
                payload.get(
                    "code",
                    "",
                )
            )

            if code not in (
                "",
                "00000",
            ):
                raise RuntimeError(
                    "Bitget API error "
                    f"{code}: "
                    f"{payload.get('msg')}"
                )

            return payload.get(
                "data"
            )

        except Exception as exc:

            last_error = exc

            if attempt >= MAX_RETRIES:
                break

            time.sleep(delay)

            delay = min(
                delay * 2,
                30,
            )

    raise RuntimeError(
        "Bitget market-data request "
        f"failed after {MAX_RETRIES} attempts: "
        f"{repr(last_error)}"
    )


# ============================================================
# BASIC MARKET DATA
# ============================================================


def get_all_futures_tickers() -> List[Dict]:
    """
    Returns all USDT perpetual futures tickers.
    """

    data = _request(
        "/api/v2/mix/market/tickers",
        params={
            "productType":
            PRODUCT_TYPE,
        },
    )

    if not isinstance(
        data,
        list,
    ):
        return []

    return data


def get_ticker(
    symbol: str,
) -> Optional[Dict]:
    """
    Returns one USDT futures ticker.
    """

    symbol = symbol.upper().strip()

    data = _request(
        "/api/v2/mix/market/ticker",
        params={
            "symbol":
            symbol,

            "productType":
            PRODUCT_TYPE,
        },
    )

    if isinstance(
        data,
        list,
    ):
        if data:
            return data[0]

        return None

    if isinstance(
        data,
        dict,
    ):
        return data

    return None


# ============================================================
# CONTRACT INFORMATION
# ============================================================


def get_contracts() -> List[Dict]:
    """
    Returns Bitget USDT futures contract information.
    """

    data = _request(
        "/api/v2/mix/market/contracts",
        params={
            "productType":
            PRODUCT_TYPE,
        },
    )

    if not isinstance(
        data,
        list,
    ):
        return []

    return data


def get_tradeable_symbols() -> List[str]:
    """
    Builds the list of currently tradeable
    USDT futures contracts.
    """

    contracts = get_contracts()

    symbols = []

    for contract in contracts:

        symbol = (
            contract.get("symbol")
            or ""
        ).upper().strip()

        status = str(
            contract.get(
                "symbolStatus",
                "",
            )
        ).lower()

        if not symbol:
            continue

        if not symbol.endswith(
            "USDT"
        ):
            continue

        if status and status not in (
            "normal",
            "listed",
        ):
            continue

        symbols.append(
            symbol
        )

    return sorted(
        set(symbols)
    )


# ============================================================
# CANDLES
# ============================================================


VALID_GRANULARITIES = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1H",
    "4H",
    "6H",
    "12H",
    "1D",
    "3D",
    "1W",
}


def get_candles(
    symbol: str,
    granularity: str,
    limit: int = 200,
) -> List[Dict[str, float]]:
    """
    Returns normalized Bitget futures candles.

    Output:
    [
        {
            "timestamp": ...,
            "open": ...,
            "high": ...,
            "low": ...,
            "close": ...,
            "volume_base": ...,
            "volume_quote": ...
        }
    ]

    Candles are sorted oldest -> newest.
    """

    symbol = symbol.upper().strip()

    if granularity not in (
        VALID_GRANULARITIES
    ):
        raise ValueError(
            "Unsupported Bitget "
            f"granularity: {granularity}"
        )

    limit = max(
        20,
        min(
            int(limit),
            1000,
        ),
    )

    data = _request(
        "/api/v2/mix/market/candles",
        params={
            "symbol":
            symbol,

            "productType":
            PRODUCT_TYPE,

            "granularity":
            granularity,

            "limit":
            limit,
        },
    )

    if not isinstance(
        data,
        list,
    ):
        return []

    candles = []

    for row in data:

        if (
            not isinstance(
                row,
                (list, tuple),
            )
            or len(row) < 6
        ):
            continue

        try:

            candle = {
                "timestamp":
                int(row[0]),

                "open":
                float(row[1]),

                "high":
                float(row[2]),

                "low":
                float(row[3]),

                "close":
                float(row[4]),

                "volume_base":
                float(row[5]),

                "volume_quote":
                (
                    float(row[6])
                    if len(row) > 6
                    else None
                ),
            }

            candles.append(
                candle
            )

        except Exception:
            continue

    candles.sort(
        key=lambda x:
        x["timestamp"]
    )

    return candles


# ============================================================
# MULTI-TIMEFRAME SNAPSHOT
# ============================================================


DEFAULT_TIMEFRAMES = (
    "5m",
    "15m",
    "30m",
    "1H",
    "4H",
    "1D",
)


def get_multi_timeframe_candles(
    symbol: str,
    timeframes=DEFAULT_TIMEFRAMES,
    limit: int = 200,
) -> Dict[str, List[Dict]]:
    """
    Fetches several timeframes for one symbol.

    This becomes the raw input for the
    technical-analysis engine.
    """

    result = {}

    for timeframe in timeframes:

        try:

            result[timeframe] = (
                get_candles(
                    symbol=symbol,
                    granularity=timeframe,
                    limit=limit,
                )
            )

        except Exception as exc:

            print(
                "Bitget candle error:",
                symbol,
                timeframe,
                repr(exc),
                flush=True,
            )

            result[timeframe] = []

    return result


# ============================================================
# ORDER BOOK
# ============================================================


def get_order_book(
    symbol: str,
    limit: int = 50,
) -> Dict:
    """
    Reads the current Bitget futures order book.

    Useful later for:
    - bid/ask imbalance
    - liquidity
    - spread
    - potential support/resistance
    """

    symbol = symbol.upper().strip()

    data = _request(
        "/api/v2/mix/market/merge-depth",
        params={
            "symbol":
            symbol,

            "productType":
            PRODUCT_TYPE,

            "precision":
            "scale0",

            "limit":
            max(
                5,
                min(
                    int(limit),
                    100,
                ),
            ),
        },
    )

    if not isinstance(
        data,
        dict,
    ):
        return {
            "bids": [],
            "asks": [],
        }

    return data


# ============================================================
# RECENT TRADES
# ============================================================


def get_recent_market_trades(
    symbol: str,
    limit: int = 100,
) -> List[Dict]:
    """
    Reads recent public market trades.

    This can later help detect:
    - aggressive buying
    - aggressive selling
    - trade-flow acceleration
    - unusual activity
    """

    symbol = symbol.upper().strip()

    data = _request(
        "/api/v2/mix/market/fills",
        params={
            "symbol":
            symbol,

            "productType":
            PRODUCT_TYPE,

            "limit":
            max(
                20,
                min(
                    int(limit),
                    1000,
                ),
            ),
        },
    )

    if not isinstance(
        data,
        list,
    ):
        return []

    return data


# ============================================================
# MARKET CONTEXT
# ============================================================


def get_major_market_context() -> Dict:
    """
    Pulls BTC and ETH market data.

    Signals Bot 2.0 will use these as
    broader market context rather than
    analysing altcoins in isolation.
    """

    context = {}

    for symbol in (
        "BTCUSDT",
        "ETHUSDT",
    ):

        try:

            context[symbol] = {
                "ticker":
                get_ticker(symbol),

                "candles":
                get_multi_timeframe_candles(
                    symbol=symbol,
                    timeframes=(
                        "15m",
                        "1H",
                        "4H",
                        "1D",
                    ),
                    limit=200,
                ),
            }

        except Exception as exc:

            context[symbol] = {
                "error":
                repr(exc)
            }

    return context


# ============================================================
# SELF TEST
# ============================================================


def bitget_public_self_test() -> bool:
    """
    Confirms that Signals Bot 2.0 can
    read Bitget public futures data.

    No API key is required for this test.
    """

    ticker = get_ticker(
        "BTCUSDT"
    )

    if not ticker:
        raise RuntimeError(
            "Bitget BTCUSDT ticker "
            "was empty."
        )

    candles = get_candles(
        symbol="BTCUSDT",
        granularity="1H",
        limit=30,
    )

    if len(candles) < 20:
        raise RuntimeError(
            "Bitget BTCUSDT candle "
            "test returned too little data."
        )

    print(
        "BITGET PUBLIC MARKET DATA: OK",
        flush=True,
    )

    print(
        f"BTCUSDT candles received: "
        f"{len(candles)}",
        flush=True,
    )

    return True


def bitget_private_credentials_test() -> bool:
    """
    Only verifies that the dedicated
    Signals Bot 2.0 credentials exist.

    It deliberately does NOT place,
    modify or cancel anything.

    Private API functionality is not
    required for public market scanning.
    """

    if not private_credentials_available():

        print(
            "Signals Bot 2.0 private "
            "Bitget credentials: NOT SET",
            flush=True,
        )

        return False

    print(
        "Signals Bot 2.0 dedicated "
        "Bitget credentials: PRESENT",
        flush=True,
    )

    return True


# ============================================================
# DIRECT TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- BITGET MARKET DATA TEST",
        flush=True,
    )

    print(
        "READ ONLY - "
        "NO TRADE EXECUTION CODE",
        flush=True,
    )

    bitget_public_self_test()

    bitget_private_credentials_test()

    print(
        "TEST COMPLETE",
        flush=True,
    )
