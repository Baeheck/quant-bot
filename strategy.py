import pandas as pd

def compute_signals(prices: pd.Series, short_window: int = 50, long_window: int = 200) -> pd.DataFrame:
    """
    Moving Average Crossover strategy.

    Logic:
    - Calculate short MA (default 50-day) and long MA (default 200-day)
    - Signal = 1 (invested) when short MA > long MA
    - Signal = 0 (cash) when short MA < long MA
    - A Golden Cross is where signal flips from 0 to 1 (buy)
    - A Death Cross is where signal flips from 1 to 0 (sell)

    Returns a DataFrame with prices, both MAs, and the signal column.
    """
    df = pd.DataFrame({"price": prices})
    df["ma_short"] = df["price"].rolling(short_window).mean()
    df["ma_long"] = df["price"].rolling(long_window).mean()

    # Signal: 1 = long, 0 = cash. Shift by 1 so we act on tomorrow's open, not today's close.
    df["signal"] = (df["ma_short"] > df["ma_long"]).astype(int).shift(1)

    # Mark crossover points
    df["crossover"] = df["signal"].diff()
    # crossover == 1 → Golden Cross (buy), crossover == -1 → Death Cross (sell)

    return df.dropna()


def current_signal(df: pd.DataFrame) -> dict:
    """Returns a plain summary of today's signal state."""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    state = "LONG (invested)" if latest["signal"] == 1 else "CASH (out of market)"
    ma_gap_pct = (latest["ma_short"] - latest["ma_long"]) / latest["ma_long"] * 100

    # Find the most recent crossover
    crossovers = df[df["crossover"] != 0]
    last_cross = crossovers.iloc[-1] if not crossovers.empty else None

    return {
        "state": state,
        "invested": latest["signal"] == 1,
        "price": round(float(latest["price"]), 2),
        "ma_short": round(float(latest["ma_short"]), 2),
        "ma_long": round(float(latest["ma_long"]), 2),
        "ma_gap_pct": round(float(ma_gap_pct), 2),
        "last_cross_date": last_cross.name.strftime("%Y-%m-%d") if last_cross is not None else "N/A",
        "last_cross_type": "Golden Cross (BUY)" if (last_cross is not None and last_cross["crossover"] == 1) else "Death Cross (SELL)",
    }
