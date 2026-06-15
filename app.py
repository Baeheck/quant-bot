import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data import TICKERS, fetch_prices
from strategy import compute_signals, current_signal
from backtester import run_backtest
from ai_brief import generate_trading_brief

st.set_page_config(page_title="Quant Trading Bot", page_icon="🤖", layout="wide")
st.title("🤖 Quantitative Trading Bot")
st.markdown("Moving average crossover strategy — backtested against real data, compared to buy-and-hold.")

# --- Sidebar controls ---
st.sidebar.header("Settings")
ticker = st.sidebar.selectbox("Asset", list(TICKERS.keys()), format_func=lambda t: f"{t} — {TICKERS[t]}")
short_w = st.sidebar.slider("Short MA (days)", 10, 100, 50)
long_w = st.sidebar.slider("Long MA (days)", 50, 300, 200)

if short_w >= long_w:
    st.sidebar.error("Short MA must be smaller than Long MA.")
    st.stop()

# --- Data ---
@st.cache_data(ttl=3600)
def load(ticker, short_w, long_w):
    prices = fetch_prices(ticker, period="5y")
    return compute_signals(prices, short_w, long_w)

with st.spinner("Fetching data..."):
    df = load(ticker, short_w, long_w)

sig = current_signal(df)

# --- Current signal banner ---
color = "green" if sig["invested"] else "orange"
st.markdown(
    f"<div style='background:{color}22;border-left:4px solid {color};"
    f"padding:12px 16px;border-radius:6px;margin-bottom:16px'>"
    f"<strong>Current signal: {sig['state']}</strong> &nbsp;|&nbsp; "
    f"Price: {sig['price']} &nbsp;|&nbsp; "
    f"50-day MA: {sig['ma_short']} &nbsp;|&nbsp; "
    f"200-day MA: {sig['ma_long']} &nbsp;|&nbsp; "
    f"MA gap: {sig['ma_gap_pct']:+.2f}% &nbsp;|&nbsp; "
    f"Last crossover: {sig['last_cross_date']} ({sig['last_cross_type']})"
    f"</div>",
    unsafe_allow_html=True,
)

# --- Price chart with MAs and crossover markers ---
st.header("Price Chart with Moving Averages")

golden = df[df["crossover"] == 1]
death = df[df["crossover"] == -1]

fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["price"], mode="lines", name="Price",
    line=dict(color="#aaaaaa", width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["ma_short"], mode="lines",
    name=f"{short_w}-day MA", line=dict(color="#636efa", width=1.5)))
fig.add_trace(go.Scatter(x=df.index, y=df["ma_long"], mode="lines",
    name=f"{long_w}-day MA", line=dict(color="#ef553b", width=1.5)))

# Golden Cross markers (buy)
fig.add_trace(go.Scatter(x=golden.index, y=golden["price"], mode="markers",
    name="Golden Cross (BUY)", marker=dict(color="lime", size=10, symbol="triangle-up")))

# Death Cross markers (sell)
fig.add_trace(go.Scatter(x=death.index, y=death["price"], mode="markers",
    name="Death Cross (SELL)", marker=dict(color="red", size=10, symbol="triangle-down")))

fig.update_layout(template="plotly_dark", height=480, hovermode="x unified",
    xaxis_title="Date", yaxis_title="Price")
st.plotly_chart(fig, use_container_width=True)

st.caption(f"Golden Cross = {short_w}-day MA crosses above {long_w}-day MA → strategy goes long. "
           f"Death Cross = crosses below → strategy moves to cash.")

# ----------------------------------------------------------------
# Backtest results
# ----------------------------------------------------------------
st.divider()
st.header("Backtest Results")

initial = st.number_input("Starting capital", min_value=100.0, value=10000.0, step=500.0)
result = run_backtest(df, initial)
bdf = result["df"]

# Equity curve
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=bdf.index, y=bdf["strategy_value"], mode="lines",
    name="Strategy (MA crossover)", line=dict(color="#00cc96", width=2)))
fig2.add_trace(go.Scatter(x=bdf.index, y=bdf["bah_value"], mode="lines",
    name="Buy-and-hold", line=dict(color="#636efa", width=2, dash="dash")))
fig2.update_layout(template="plotly_dark", height=400, hovermode="x unified",
    xaxis_title="Date", yaxis_title=f"Portfolio value (starting {initial:,.0f})")
st.plotly_chart(fig2, use_container_width=True)

# Metrics side by side
st.subheader("Performance comparison")
metrics = result["metrics"]
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Strategy (MA crossover)**")
    for k, v in metrics.items():
        if "Strategy" in k or k in ["Time in market", "Number of completed trades", "Win rate"]:
            label = k.replace("Strategy ", "")
            st.markdown(f"- {label}: **{v}**")
with col2:
    st.markdown("**Buy-and-hold**")
    for k, v in metrics.items():
        if "Buy-and-hold" in k:
            label = k.replace("Buy-and-hold ", "")
            st.markdown(f"- {label}: **{v}**")

# Trade log
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
        brief = generate_trading_brief(sig, result["metrics"], trades_summary, ticker, short_w, long_w)
    st.markdown(brief)
