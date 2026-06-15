import pandas as pd
import numpy as np


def run_backtest(df: pd.DataFrame, initial_capital: float = 10000.0) -> dict:
    """
    Simulates the MA crossover strategy against buy-and-hold.

    signal = 1  → long (profit when price rises)
    signal = 0  → cash (no return)
    signal = -1 → short (profit when price falls)

    strategy_return = signal * daily_return handles all three automatically.
    """
    df = df.copy()
    short_mode = bool((df["signal"] == -1).any())

    df["daily_return"] = df["price"].pct_change().fillna(0)
    df["strategy_return"] = df["signal"] * df["daily_return"]
    df["strategy_value"] = initial_capital * (1 + df["strategy_return"]).cumprod()
    df["bah_value"] = initial_capital * (1 + df["daily_return"]).cumprod()

    # --- Trade log ---
    trades = []
    position = None   # "long" or "short" or None
    entry_price = None
    entry_date = None

    for date, row in df.iterrows():
        if row["crossover"] == 1:   # Golden Cross → go long
            if position == "short":
                ret = round((entry_price / row["price"] - 1) * 100, 2)
                trades.append({"Type": "Short", "Entry date": entry_date.strftime("%Y-%m-%d"),
                    "Exit date": date.strftime("%Y-%m-%d"), "Entry price": round(entry_price, 2),
                    "Exit price": round(row["price"], 2), "Return %": ret,
                    "Result": "Win" if ret > 0 else "Loss"})
            position = "long"
            entry_price = row["price"]
            entry_date = date

        elif row["crossover"] == -1:   # Death Cross → close long, go short if short_mode
            if position == "long":
                ret = round((row["price"] / entry_price - 1) * 100, 2)
                trades.append({"Type": "Long", "Entry date": entry_date.strftime("%Y-%m-%d"),
                    "Exit date": date.strftime("%Y-%m-%d"), "Entry price": round(entry_price, 2),
                    "Exit price": round(row["price"], 2), "Return %": ret,
                    "Result": "Win" if ret > 0 else "Loss"})
            if short_mode:
                position = "short"
                entry_price = row["price"]
                entry_date = date
            else:
                position = None

    # Open position
    if position is not None:
        current_price = df["price"].iloc[-1]
        if position == "long":
            ret = round((current_price / entry_price - 1) * 100, 2)
        else:
            ret = round((entry_price / current_price - 1) * 100, 2)
        trades.append({"Type": position.capitalize(), "Entry date": entry_date.strftime("%Y-%m-%d"),
            "Exit date": "Open", "Entry price": round(entry_price, 2),
            "Exit price": round(current_price, 2), "Return %": ret, "Result": "Open"})

    # --- Metrics ---
    def sharpe(r):
        r = r.dropna()
        return round((r.mean() / r.std()) * np.sqrt(252), 2) if r.std() != 0 else 0.0

    def max_dd(v):
        return round(((v - v.cummax()) / v.cummax() * 100).min(), 2)

    def tot_ret(v):
        return round((v.iloc[-1] / v.iloc[0] - 1) * 100, 2)

    completed = [t for t in trades if t["Result"] != "Open"]
    wins = [t for t in completed if t["Result"] == "Win"]
    win_rate = round(len(wins) / max(len(completed), 1) * 100, 1)

    if short_mode:
        time_label = f"Long: {round((df['signal']==1).mean()*100,1)}% / Short: {round((df['signal']==-1).mean()*100,1)}%"
    else:
        time_label = f"{round((df['signal']==1).mean()*100,1)}%"

    metrics = {
        "Strategy total return": f"{tot_ret(df['strategy_value'])}%",
        "Buy-and-hold total return": f"{tot_ret(df['bah_value'])}%",
        "Strategy Sharpe ratio": sharpe(df["strategy_return"]),
        "Buy-and-hold Sharpe ratio": sharpe(df["daily_return"]),
        "Strategy max drawdown": f"{max_dd(df['strategy_value'])}%",
        "Buy-and-hold max drawdown": f"{max_dd(df['bah_value'])}%",
        "Time in market": time_label,
        "Completed trades": len(completed),
        "Win rate": f"{win_rate}%",
    }

    return {
        "df": df,
        "metrics": metrics,
        "trades": pd.DataFrame(trades) if trades else pd.DataFrame(),
        "short_mode": short_mode,
    }
