import yfinance as yf
import pandas as pd

# Default tickers the user can choose from
TICKERS = {
    "VWCE.DE": "Vanguard FTSE All-World Acc (EUR)",
    "IWDA.L": "iShares MSCI World (GBP)",
    "VWRL.L": "Vanguard FTSE All-World Dist (GBP)",
    "WSML.L": "iShares MSCI World Small Cap (GBP)",
    "IGLN.L": "iShares Physical Gold (GBP)",
    "BTCE.DE": "ETC Group Bitcoin ETP (EUR)",
}

def fetch_prices(ticker: str, period: str = "5y") -> pd.Series:
    """Returns a clean daily closing price series for a single ticker."""
    raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"No data returned for {ticker}.")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna().rename(ticker)
