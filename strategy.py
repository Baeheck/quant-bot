import pandas as pd


def compute_signals(prices: pd.Series, short_window: int = 50, long_window: int = 200, short_mode: bool = False) -> pd.DataFrame:
    """
    Moving Average Crossover strategy.

    Long-only mode (short_mode=False):
      signal = 1 (long) when short MA > long MA
      signal = 0 (cash) when short MA < long MA

    Long/Short mode (short_mode=True):
      signal = 1 (long) when short MA > long MA
      signal = -1 (short, bet on decline) when short MA < long MA

    Crossover detection is always based on the raw MA condition:
      crossover = +1 → Golden Cross (go long)
      crossover = -1 → Death Cross (go to cash or go short)
    """
    df = pd.DataFrame({"price": prices})
    df["ma_short"] = df["price"].rolling(short_window).mean()
    df["ma_long"] = df["price"].rolling(long_window).mean()

    ma_above = (df["ma_short"] > df["ma_long"]).astype(int).shift(1)

    if short_mode:
        df["signal"] = ma_above.replace(0, -1)
    else:
        df["signal"] = ma_above

    # Crossover based on underlying MA condition (not signal) so +1/-1 is always consistent
    df["crossover"] = ma_above.diff()

    return df.dropna()


def current_signal(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    signal_val = latest["signal"]

    if signal_val == 1:
        state = "LONG (invested)"
    elif signal_val == -1:
        state = "SHORT (betting on decline)"
    else:
        state = "CASH (out of market)"

    ma_gap_pct = (latest["ma_short"] - latest["ma_long"]) / latest["ma_long"] * 100
    crossovers = df[df["crossover"] != 0]
    last_cross = crossovers.iloc[-1] if not crossovers.empty else None

    return {
        "state": state,
        "invested": signal_val != 0,
        "short": signal_val == -1,
        "price": round(float(latest["price"]), 2),
        "ma_short": round(float(latest["ma_short"]), 2),
        "ma_long": round(float(latest["ma_long"]), 2),
        "ma_gap_pct": round(float(ma_gap_pct), 2),
        "last_cross_date": last_cross.name.strftime("%Y-%m-%d") if last_cross is not None else "N/A",
        "last_cross_type": "Golden Cross (BUY)" if (last_cross is not None and last_cross["crossover"] == 1) else "Death Cross (SELL/SHORT)",
    }
