import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize

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

st.sidebar.caption("💡 Example: AAPL, MSFT, GOOGL")

# ==============================
# BUTTON ACTION
# ==============================
if st.sidebar.button("Analyze Portfolio"):

    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip() != ""]

    if len(stocks) == 0:
        st.error("❌ Please enter at least one stock")
        st.stop()

    # ==============================
    # DOWNLOAD DATA
    # ==============================
    data = yf.download(stocks, start="2020-01-01")

# Fix multi-stock structure
if isinstance(data.columns, pd.MultiIndex):
    data = data["Close"]

# Drop stocks with no data
data = data.dropna(axis=1, how="all")

# If nothing left
if data.shape[1] == 0:
    st.error("❌ No valid stock data found")
    st.stop()

# Align data (important!)
data = data.dropna()

returns = data.pct_change().dropna()

# Final safety check
if returns.empty:
    st.error("❌ Not enough data to calculate returns")
    st.stop()

    # ==============================
    # OPTIMIZATION FUNCTION
    # ==============================
    def portfolio_volatility(weights):
        return np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))

    num_assets = len(stocks)

    constraints = ({
        "type": "eq",
        "fun": lambda x: np.sum(x) - 1
    })

    bounds = tuple((0, 1) for _ in range(num_assets))

    initial_weights = np.ones(num_assets) / num_assets

    result = minimize(
        portfolio_volatility,
        initial_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints
    )

    weights = result.x

    # ==============================
    # METRICS
    # ==============================
    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = portfolio_volatility(weights)
    sharpe = port_return / port_vol

    cumulative = (1 + returns.dot(weights)).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()

    # ==============================
    # DISPLAY METRICS
    # ==============================
    st.subheader("📊 Optimized Portfolio Metrics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Return", f"{port_return*100:.2f}%")
    col2.metric("Volatility", f"{port_vol*100:.2f}%")
    col3.metric("Sharpe", f"{sharpe:.2f}")
    col4.metric("Max Drawdown", f"{drawdown*100:.2f}%")

    # ==============================
    # ALLOCATION
    # ==============================
    st.subheader("📊 Optimized Allocation")

    allocation_df = pd.DataFrame({
        "Stock": stocks,
        "Weight": weights
    })

    st.bar_chart(allocation_df.set_index("Stock"))

    st.dataframe(allocation_df)

    # ==============================
    # GROWTH
    # ==============================
    st.subheader("📈 Portfolio Growth")

    st.line_chart(cumulative)
