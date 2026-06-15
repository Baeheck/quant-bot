import streamlit as st
import plotly.graph_objects as go
from data import TICKERS, fetch_prices
from strategy import compute_signals, current_signal
from backtester import run_backtest
from ai_brief import generate_trading_brief

st.set_page_config(page_title="Quant Trading Bot", page_icon="🤖", layout="wide")
st.title("🤖 Quantitative Trading Bot")
st.markdown("Moving average crossover strategy — backtested against real data, compared to buy-and-hold.")

# ----------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------
st.sidebar.header("Settings")

custom = st.sidebar.text_input("Any Yahoo Finance ticker (e.g. NVDA, BTC-USD, MSFT)", "").strip().upper()
if custom:
    ticker = custom
    ticker_label = custom
else:
    ticker = st.sidebar.selectbox("Or choose a preset ETF", list(TICKERS.keys()),
        format_func=lambda t: f"{t} — {TICKERS[t]}")
    ticker_label = ticker

short_w = st.sidebar.slider("Short MA (days)", 10, 100, 50)
long_w = st.sidebar.slider("Long MA (days)", 50, 300, 200)
short_mode = st.sidebar.toggle("Short mode — profit from declines", value=False)

if short_w >= long_w:
    st.sidebar.error("Short MA must be smaller than Long MA.")
    st.stop()

if short_mode:
    st.sidebar.info("Short mode ON: at a Death Cross the bot goes SHORT — it bets the asset will keep falling and profits if it does.")

# ----------------------------------------------------------------
# Data
# ----------------------------------------------------------------
@st.cache_data(ttl=3600)
def load(ticker, short_w, long_w, short_mode):
    prices = fetch_prices(ticker, period="5y")
    return compute_signals(prices, short_w, long_w, short_mode)

try:
    with st.spinner(f"Fetching data for {ticker_label}..."):
        df = load(ticker, short_w, long_w, short_mode)
except Exception as e:
    st.error(f"Could not load data for '{ticker}'. Check the ticker symbol and try again. ({e})")
    st.stop()

sig = current_signal(df)

# ----------------------------------------------------------------
# Signal banner
# ----------------------------------------------------------------
if sig["short"]:
    color, icon = "#ef553b", "SHORT"
elif sig["invested"]:
    color, icon = "green", "LONG"
else:
    color, icon = "orange", "CASH"

st.markdown(
    f"<div style='background:{color}22;border-left:4px solid {color};"
    f"padding:12px 16px;border-radius:6px;margin-bottom:16px'>"
    f"<strong>Current signal: {sig['state']}</strong> &nbsp;|&nbsp; "
    f"Price: {sig['price']} &nbsp;|&nbsp; "
    f"{short_w}-day MA: {sig['ma_short']} &nbsp;|&nbsp; "
    f"{long_w}-day MA: {sig['ma_long']} &nbsp;|&nbsp; "
    f"MA gap: {sig['ma_gap_pct']:+.2f}% &nbsp;|&nbsp; "
    f"Last crossover: {sig['last_cross_date']} ({sig['last_cross_type']})"
    f"</div>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------
# Price chart
# ----------------------------------------------------------------
st.header(f"Price Chart — {ticker_label}")

golden = df[df["crossover"] == 1]
death  = df[df["crossover"] == -1]

fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["price"], mode="lines", name="Price",
    line=dict(color="#aaaaaa", width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["ma_short"], mode="lines",
    name=f"{short_w}-day MA", line=dict(color="#636efa", width=1.5)))
fig.add_trace(go.Scatter(x=df.index, y=df["ma_long"], mode="lines",
    name=f"{long_w}-day MA", line=dict(color="#ef553b", width=1.5)))
fig.add_trace(go.Scatter(x=golden.index, y=golden["price"], mode="markers",
    name="Golden Cross (BUY)", marker=dict(color="lime", size=10, symbol="triangle-up")))
fig.add_trace(go.Scatter(x=death.index, y=death["price"], mode="markers",
    name="Death Cross (SELL/SHORT)", marker=dict(color="red", size=10, symbol="triangle-down")))

fig.update_layout(template="plotly_dark", height=480, hovermode="x unified",
    xaxis_title="Date", yaxis_title="Price")
st.plotly_chart(fig, use_container_width=True)

mode_label = "goes SHORT (bets on decline)" if short_mode else "moves to cash"
st.caption(f"Golden Cross = {short_w}-day MA crosses above {long_w}-day MA → go long. "
           f"Death Cross = crosses below → {mode_label}.")

# ----------------------------------------------------------------
# Backtest
# ----------------------------------------------------------------
st.divider()
st.header("Backtest Results")

initial = st.number_input("Starting capital", min_value=100.0, value=10000.0, step=500.0)
result = run_backtest(df, initial)
bdf = result["df"]

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=bdf.index, y=bdf["strategy_value"], mode="lines",
    name="Strategy", line=dict(color="#00cc96", width=2)))
fig2.add_trace(go.Scatter(x=bdf.index, y=bdf["bah_value"], mode="lines",
    name="Buy-and-hold", line=dict(color="#636efa", width=2, dash="dash")))
fig2.update_layout(template="plotly_dark", height=400, hovermode="x unified",
    xaxis_title="Date", yaxis_title=f"Portfolio value (starting {initial:,.0f})")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Performance comparison")
metrics = result["metrics"]
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Strategy**")
    for k, v in metrics.items():
        if "Strategy" in k or k in ["Time in market", "Completed trades", "Win rate"]:
            st.markdown(f"- {k.replace('Strategy ', '')}: **{v}**")
with col2:
    st.markdown("**Buy-and-hold**")
    for k, v in metrics.items():
        if "Buy-and-hold" in k:
            st.markdown(f"- {k.replace('Buy-and-hold ', '')}: **{v}**")

if not result["trades"].empty:
    st.subheader("Trade log")
    st.dataframe(result["trades"], use_container_width=True)

# ----------------------------------------------------------------
# AI Trading Brief
# ----------------------------------------------------------------
st.divider()
st.header("AI Trading Brief")
st.markdown("Claude reads the live signal, backtest results, and trade history — then gives you a plain-English assessment.")

if st.button("Generate Trading Brief", type="primary"):
    trades_summary = result["trades"].to_string(index=False) if not result["trades"].empty else "No completed trades."
    with st.spinner("Analysing strategy..."):
        brief = generate_trading_brief(sig, result["metrics"], trades_summary, ticker_label, short_w, long_w)
    st.markdown(brief)
