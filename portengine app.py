import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

st.title("🚀 Portfolio Intelligence Pro")

# ==============================
# SIDEBAR INPUT
# ==============================
st.sidebar.header("📥 Portfolio Input")

stocks_input = st.sidebar.text_area(
    "Stocks (comma separated)",
    "AAPL,MSFT,GOOGL"
)

investment = st.sidebar.number_input("💰 Total Investment (₹)", value=100000)

risk_free_rate = st.sidebar.slider("📊 Risk-Free Rate (%)", 0.0, 10.0, 5.0) / 100

benchmark_choice = st.sidebar.selectbox(
    "📈 Benchmark",
    ["^GSPC", "^NSEI"]
)

# ==============================
# MAIN BUTTON
# ==============================
if st.sidebar.button("Analyze Portfolio"):

    # --------------------------
    # CLEAN INPUT
    # --------------------------
    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

    if len(stocks) == 0:
        st.error("❌ Please enter at least one stock")
        st.stop()

    # --------------------------
    # DOWNLOAD DATA
    # --------------------------
    data = yf.download(stocks, start="2020-01-01", progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    data = data.dropna(axis=1, how="all")

    if data.shape[1] == 0:
        st.error("❌ Invalid stocks entered")
        st.stop()

    data = data.dropna()
    returns = data.pct_change().dropna()

    if returns.empty:
        st.error("❌ Not enough data")
        st.stop()

    # --------------------------
    # BENCHMARK
    # --------------------------
    benchmark = yf.download(benchmark_choice, start="2020-01-01", progress=False)["Close"]
    benchmark_returns = benchmark.pct_change().dropna()

    combined = pd.concat([returns, benchmark_returns], axis=1).dropna()
    returns = combined.iloc[:, :-1]
    benchmark_returns = combined.iloc[:, -1]

    # --------------------------
    # OPTIMIZATION (MAX SHARPE)
    # --------------------------
    def neg_sharpe(weights):
        port_return = np.sum(returns.mean() * weights) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        return -(port_return - risk_free_rate) / port_vol

    num_assets = len(returns.columns)

    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(num_assets))
    initial = np.ones(num_assets) / num_assets

    result = minimize(
        neg_sharpe,
        initial,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints
    )

    weights = result.x

    # --------------------------
    # METRICS
    # --------------------------
    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol != 0 else 0

    cumulative = (1 + returns.dot(weights)).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()

    covariance = np.cov(returns.dot(weights), benchmark_returns)[0][1]
    beta = covariance / np.var(benchmark_returns)

    # ==============================
    # DISPLAY METRICS
    # ==============================
    st.subheader("📊 Portfolio Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Return", f"{port_return*100:.2f}%")
    col2.metric("Volatility", f"{port_vol*100:.2f}%")
    col3.metric("Sharpe", f"{sharpe:.2f}")
    col4.metric("Max Drawdown", f"{drawdown*100:.2f}%")
    col5.metric("Beta", f"{beta:.2f}")

    # ==============================
    # RECOMMENDATION (CORRECT POSITION)
    # ==============================
    st.subheader("📌 Recommendation")

    if sharpe > 1:
        st.success("✅ Strong portfolio — hold or increase allocation")
    elif sharpe > 0.5:
        st.warning("⚠️ Average performance — consider optimization")
    else:
        st.error("❌ Weak portfolio — reallocation recommended")

    # ==============================
    # ALLOCATION
    # ==============================
    st.subheader("📊 Allocation")

    allocation_df = pd.DataFrame({
        "Stock": returns.columns,
        "Weight (%)": weights * 100,
        "Investment (₹)": weights * investment
    }).sort_values(by="Weight (%)", ascending=False)

    st.bar_chart(allocation_df.set_index("Stock")["Weight (%)"])
    st.dataframe(allocation_df)

    # ==============================
    # GROWTH VS BENCHMARK
    # ==============================
    st.subheader("📈 Portfolio vs Benchmark")

    portfolio_growth = (1 + returns.dot(weights)).cumprod()
    benchmark_growth = (1 + benchmark_returns).cumprod()

    growth_df = pd.DataFrame({
        "Portfolio": portfolio_growth,
        "Benchmark": benchmark_growth
    })

    st.line_chart(growth_df)

    # ==============================
    # INSIGHTS
    # ==============================
    st.subheader("🧠 Insights")

    best_stock = allocation_df.iloc[0]["Stock"]

    st.success(f"Top allocation: {best_stock}")
    st.info(f"Sharpe Ratio: {sharpe:.2f}")
