import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence", layout="wide")

st.title("🚀 Portfolio Intelligence Dashboard")

# ==============================
# SIDEBAR INPUT
# ==============================
st.sidebar.header("📥 Enter Your Portfolio")

stocks_input = st.sidebar.text_area(
    "Enter stocks (comma separated)",
    "AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_area(
    "Enter weights (comma separated)",
    "0.3,0.4,0.3"
)

st.sidebar.caption("💡 Example: AAPL, MSFT, GOOGL")
st.sidebar.caption("💡 Weights must sum to 1 (e.g., 0.3, 0.4, 0.3)")

# ==============================
# BUTTON ACTION
# ==============================
if st.sidebar.button("Analyze Portfolio"):

    # ==============================
    # INPUT CLEANING
    # ==============================
    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip() != ""]
    weights_raw = [w.strip() for w in weights_input.split(",") if w.strip() != ""]

    # Convert weights safely
    try:
        weights = np.array(list(map(float, weights_raw)))
    except:
        st.error("❌ Weights must be numbers")
        st.stop()

    # ==============================
    # VALIDATIONS
    # ==============================
    if len(stocks) == 0:
        st.error("❌ Please enter at least one stock")
        st.stop()

    if len(stocks) != len(weights):
        st.error("❌ Number of stocks and weights must match")
        st.stop()

    if abs(sum(weights) - 1) > 0.01:
        st.warning("⚠️ Weights should sum to 1 (100%)")

    # ==============================
    # DOWNLOAD DATA
    # ==============================
    data = yf.download(stocks, start="2020-01-01")

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    if data.isnull().all().all():
        st.error("❌ Could not fetch stock data. Check symbols.")
        st.stop()

    # ==============================
    # RETURNS
    # ==============================
    returns = data.pct_change().dropna()

    # ==============================
    # METRICS
    # ==============================
    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = port_return / port_vol

    cumulative = (1 + returns.dot(weights)).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()

    # ==============================
    # DISPLAY METRICS
    # ==============================
    st.subheader("📊 Live Portfolio Metrics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Return", f"{port_return*100:.2f}%")
    col2.metric("Volatility", f"{port_vol*100:.2f}%")
    col3.metric("Sharpe", f"{sharpe:.2f}")
    col4.metric("Max Drawdown", f"{drawdown*100:.2f}%")

    # ==============================
    # ALLOCATION
    # ==============================
    st.subheader("📊 Portfolio Allocation")

    allocation_df = pd.DataFrame({
        "Stock": stocks,
        "Weight": weights
    })

    st.bar_chart(allocation_df.set_index("Stock"))

    # ==============================
    # GROWTH
    # ==============================
    st.subheader("📈 Portfolio Growth")

    st.line_chart(cumulative)

    # ==============================
    # SIGNALS
    # ==============================
    st.subheader("💡 Buy / Sell Signals")

    signals = []

    for stock in stocks:
        if returns[stock].mean() > 0:
            signals.append("BUY")
        else:
            signals.append("SELL")

    signal_df = pd.DataFrame({
        "Stock": stocks,
        "Weight": weights,
        "Signal": signals
    })

    st.dataframe(signal_df)
