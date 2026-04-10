import streamlit as st
import pandas as pd

st.set_page_config(page_title="Portfolio Intelligence", layout="wide")

st.title("🚀 Portfolio Intelligence Dashboard")


output = pd.read_excel("portfolio_output.xlsx")
weights = pd.read_excel("portfolio_weights.xlsx")
growth = pd.read_excel("portfolio_growth.xlsx")
signals = pd.read_excel("signals.xlsx")
# ==============================
# METRICS (TOP CARDS)
# ==============================
st.subheader("📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Return", f"{output.iloc[0,1]*100:.2f}%")
col2.metric("Volatility", f"{output.iloc[1,1]*100:.2f}%")
col3.metric("Sharpe", f"{output.iloc[2,1]:.2f}")
col4.metric("Max Drawdown", f"{output.iloc[3,1]*100:.2f}%")

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
