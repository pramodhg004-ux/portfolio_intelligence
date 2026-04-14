import streamlit as st
import pandas as pd

st.set_page_config(page_title="Portfolio Intelligence", layout="wide")

st.title("🚀 Portfolio Intelligence Dashboard")


# ==============================
# SIDEBAR INPUT
# ==============================
st.sidebar.header("📥 Enter Your Portfolio")

stocks_input = st.sidebar.text_input(
    "Enter stocks (comma separated)",
    "AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_input(
    "Enter weights (comma separated)",
    "0.3,0.4,0.3"
)

# ==============================
# BUTTON ACTION
# ==============================
if st.sidebar.button("Analyze Portfolio"):

    stocks = [s.strip() for s in stocks_input.split(",")]
    weights = np.array(list(map(float, weights_input.split(","))))

    data = yf.download(stocks, start="2020-01-01")["Close"]
    returns = data.pct_change().dropna()

    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = port_return / port_vol

    st.subheader("📊 Live Portfolio Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Return", f"{port_return*100:.2f}%")
    col2.metric("Volatility", f"{port_vol*100:.2f}%")
    col3.metric("Sharpe", f"{sharpe:.2f}")

    growth = (1 + returns.dot(weights)).cumprod()

    st.subheader("📈 Portfolio Growth")
    st.line_chart(growth)

# ==============================
# ALLOCATION
# ==============================
st.subheader("📊 Portfolio Allocation")
st.bar_chart(weights.set_index("Stock"))

# ==============================
# GROWTH
# ==============================
st.subheader("📈 Portfolio Growth")
st.line_chart(growth.set_index("Date"))

# ==============================
# SIGNALS
# ==============================
st.subheader("💡 Buy / Sell Signals")
st.dataframe(signals)
import yfinance as yf
import numpy as np
if st.sidebar.button("Analyze Portfolio"):

    stocks = [s.strip() for s in stocks_input.split(",")]
    weights = np.array(list(map(float, weights_input.split(","))))

    data = yf.download(stocks, start="2020-01-01")["Close"]

    returns = data.pct_change().dropna()

    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = port_return / port_vol

    st.subheader("📊 Live Portfolio Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Return", f"{port_return*100:.2f}%")
    col2.metric("Volatility", f"{port_vol*100:.2f}%")
    col3.metric("Sharpe", f"{sharpe:.2f}")

    growth = (1 + returns.dot(weights)).cumprod()

    st.subheader("📈 Portfolio Growth")
    st.line_chart(growth)
    st.sidebar.header("📥 Enter Your Portfolio")

stocks_input = st.sidebar.text_input(
    "Enter stocks (comma separated)",
    "AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_input(
    "Enter weights (comma separated)",
    "0.3,0.4,0.3"
)
st.sidebar.header("📥 Enter Your Portfolio")

stocks_input = st.sidebar.text_input(
    "Enter stocks (comma separated)",
    "AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_input(
    "Enter weights (comma separated)",
    "0.3,0.4,0.3"
)
