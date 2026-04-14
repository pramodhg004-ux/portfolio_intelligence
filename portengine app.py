import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")
st.title("🚀 Portfolio Intelligence Pro")

# ==============================
# SESSION STORAGE
# ==============================
if "saved_portfolios" not in st.session_state:
    st.session_state.saved_portfolios = []

# ==============================
# SIDEBAR INPUT
# ==============================
st.sidebar.header("📥 Portfolio Input")

stocks_input = st.sidebar.text_area("Stocks", "AAPL,MSFT,GOOGL")
investment = st.sidebar.number_input("💰 Investment (₹)", value=100000)
risk_free_rate = st.sidebar.slider("Risk-Free Rate (%)", 0.0, 10.0, 5.0) / 100

benchmark_choice = st.sidebar.selectbox("Benchmark", ["^GSPC", "^NSEI"])

# PREMIUM TOGGLE
st.sidebar.subheader("💎 Premium")
premium = st.sidebar.checkbox("Unlock Pro Features")

# ==============================
# MAIN BUTTON
# ==============================
if st.sidebar.button("Analyze Portfolio"):

    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

    if len(stocks) == 0:
        st.error("Enter stocks")
        st.stop()

    # DATA
    data = yf.download(stocks, start="2020-01-01", progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    data = data.dropna(axis=1, how="all").dropna()
    returns = data.pct_change().dropna()

    if returns.empty:
        st.error("No data")
        st.stop()

    # BENCHMARK
    benchmark = yf.download(benchmark_choice, start="2020-01-01", progress=False)["Close"]
    benchmark_returns = benchmark.pct_change().dropna()

    combined = pd.concat([returns, benchmark_returns], axis=1).dropna()
    returns = combined.iloc[:, :-1]
    benchmark_returns = combined.iloc[:, -1]

    # OPTIMIZATION
    def neg_sharpe(weights):
        r = np.sum(returns.mean() * weights) * 252
        v = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        return -(r - risk_free_rate) / v

    num_assets = len(returns.columns)
    bounds = tuple((0, 1) for _ in range(num_assets))
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
    initial = np.ones(num_assets) / num_assets

    result = minimize(neg_sharpe, initial, method="SLSQP",
                      bounds=bounds, constraints=constraints)

    weights = result.x

    # METRICS
    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol != 0 else 0

    cumulative = (1 + returns.dot(weights)).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()

    covariance = np.cov(returns.dot(weights), benchmark_returns)[0][1]
    beta = covariance / np.var(benchmark_returns)

    # ==============================
    # METRICS DISPLAY
    # ==============================
    st.subheader("📊 Portfolio Metrics")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Return", f"{port_return*100:.2f}%")
    c2.metric("Volatility", f"{port_vol*100:.2f}%")
    c3.metric("Sharpe", f"{sharpe:.2f}")
    c4.metric("Drawdown", f"{drawdown*100:.2f}%")
    c5.metric("Beta", f"{beta:.2f}")

    # ==============================
    # RECOMMENDATION
    # ==============================
    st.subheader("📌 Recommendation")

    if sharpe > 1:
        st.success("Strong portfolio — hold")
    elif sharpe > 0.5:
        st.warning("Average — improve allocation")
    else:
        st.error("Weak — rebalance needed")

    # ==============================
    # ALLOCATION
    # ==============================
    st.subheader("📊 Allocation")

    alloc = pd.DataFrame({
        "Stock": returns.columns,
        "Weight (%)": weights * 100,
        "Investment": weights * investment
    }).sort_values(by="Weight (%)", ascending=False)

    st.bar_chart(alloc.set_index("Stock")["Weight (%)"])
    st.dataframe(alloc)

    # ==============================
    # GROWTH
    # ==============================
    st.subheader("📈 Growth vs Benchmark")

    growth = pd.DataFrame({
        "Portfolio": (1 + returns.dot(weights)).cumprod(),
        "Benchmark": (1 + benchmark_returns).cumprod()
    })

    st.line_chart(growth)

    # ==============================
    # SAVE PORTFOLIO
    # ==============================
    if st.button("💾 Save Portfolio"):
        st.session_state.saved_portfolios.append(stocks)
        st.success("Saved!")

    # ==============================
    # SAVED LIST
    # ==============================
    st.subheader("📁 Saved Portfolios")

    for i, p in enumerate(st.session_state.saved_portfolios):
        st.write(f"{i+1}: {p}")

    # ==============================
    # PRO FEATURES
    # ==============================
    if premium:

        st.subheader("⚖️ Rebalancing")

        eq = 1 / len(weights)
        dev = np.abs(weights - eq)

        if np.max(dev) > 0.1:
            st.warning("Rebalance recommended")
        else:
            st.success("Balanced")

        st.subheader("🤖 Smart Suggestions")

        if beta > 1.2:
            st.warning("High market risk")

        if port_vol > 0.3:
            st.warning("High volatility")

        if len(stocks) < 4:
            st.warning("Low diversification")

    else:
        st.info("Unlock premium for advanced insights")
