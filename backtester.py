import pandas as pd
import numpy as np


def run_backtest(df: pd.DataFrame, initial_capital: float = 10000.0) -> dict:
    """
    Simulates the MA crossover strategy against buy-and-hold.

    Strategy: invested when signal=1, cash (0% return) when signal=0.
    Buy-and-hold: always invested from day 1.

    Returns a dict with daily portfolio values, metrics, and trade log.
    """
    df = df.copy()

    # Daily returns of the underlying asset
    df["daily_return"] = df["price"].pct_change().fillna(0)

    # Strategy return: only captures the daily return when invested
    df["strategy_return"] = df["signal"] * df["daily_return"]

    # Portfolio values
    df["strategy_value"] = initial_capital * (1 + df["strategy_return"]).cumprod()
    df["bah_value"] = initial_capital * (1 + df["daily_return"]).cumprod()

    # --- Trade log ---
    trades = []
    in_trade = False
    entry_price = None
    entry_date = None

    for date, row in df.iterrows():
        if row["crossover"] == 1 and not in_trade:
            in_trade = True
            entry_price = row["price"]
            entry_date = date
        elif row["crossover"] == -1 and in_trade:
            exit_price = row["price"]
            ret = (exit_price / entry_price - 1) * 100
            trades.append({
                "Entry date": entry_date.strftime("%Y-%m-%d"),
                "Exit date": date.strftime("%Y-%m-%d"),
                "Entry price": round(entry_price, 2),
                "Exit price": round(exit_price, 2),
                "Return %": round(ret, 2),
                "Result": "Win" if ret > 0 else "Loss",
            })
            in_trade = False

    # If still in a trade, mark it as open
    if in_trade:
        trades.append({
            "Entry date": entry_date.strftime("%Y-%m-%d"),
            "Exit date": "Open",
            "Entry price": round(entry_price, 2),
            "Exit price": round(df["price"].iloc[-1], 2),
            "Return %": round((df["price"].iloc[-1] / entry_price - 1) * 100, 2),
            "Result": "Open",
        })

    # --- Metrics ---
    def sharpe(returns_series):
        r = returns_series.dropna()
        if r.std() == 0:
            return 0.0
        return round((r.mean() / r.std()) * np.sqrt(252), 2)

    def max_drawdown(value_series):
        roll_max = value_series.cummax()
        dd = (value_series - roll_max) / roll_max * 100
        return round(dd.min(), 2)

    def total_return(value_series):
        return round((value_series.iloc[-1] / value_series.iloc[0] - 1) * 100, 2)

    pct_in_market = round(df["signal"].mean() * 100, 1)

    metrics = {
        "Strategy total return": f"{total_return(df['strategy_value'])}%",
        "Buy-and-hold total return": f"{total_return(df['bah_value'])}%",
        "Strategy Sharpe ratio": sharpe(df["strategy_return"]),
        "Buy-and-hold Sharpe ratio": sharpe(df["daily_return"]),
        "Strategy max drawdown": f"{max_drawdown(df['strategy_value'])}%",
        "Buy-and-hold max drawdown": f"{max_drawdown(df['bah_value'])}%",
        "Time in market": f"{pct_in_market}%",
        "Number of completed trades": len([t for t in trades if t['Result'] != 'Open']),
        "Win rate": f"{round(sum(1 for t in trades if t['Result'] == 'Win') / max(len([t for t in trades if t['Result'] != 'Open']), 1) * 100, 1)}%",
    }

    return {
        "df": df,
        "metrics": metrics,
        "trades": pd.DataFrame(trades) if trades else pd.DataFrame(),
    }
