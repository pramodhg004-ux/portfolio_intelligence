import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
from supabase import create_client

# ==============================
# 🔑 SUPABASE CONFIG (PUT YOURS)
# ==============================
SUPABASE_URL = "https://bveslnslwdttqzxqmrth.supabase.co"
SUPABASE_KEY = "sb_publishable_avmvZzge1AZHSRcTXF4pfg_019rj-rC"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# 🔐 LOGIN
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 Login")
    username = st.text_input("Enter Username")

    if st.button("Login"):
        if username:
            st.session_state.user = username
            st.rerun()

    st.stop()

# ==============================
# 🚀 MAIN APP
# ==============================
st.title(f"🚀 Portfolio Intelligence — {st.session_state.user}")

stocks_input = st.text_area("Stocks (comma separated)", "AAPL,MSFT,GOOGL")
investment = st.number_input("Investment ₹", value=100000)

# ==============================
# ANALYZE
# ==============================
if st.button("Analyze Portfolio"):

    stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

    if len(stocks) == 0:
        st.error("Enter valid stocks")
        st.stop()

    # DATA
    data = yf.download(stocks, start="2020-01-01", progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    data = data.dropna(axis=1, how="all").dropna()
    returns = data.pct_change().dropna()

    if returns.empty:
        st.error("No valid data")
        st.stop()

    # OPTIMIZATION
    def neg_sharpe(w):
        r = np.sum(returns.mean() * w) * 252
        v = np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
        return -r / v

    n = len(returns.columns)
    w0 = np.ones(n) / n

    res = minimize(neg_sharpe, w0,
                   bounds=[(0,1)]*n,
                   constraints={"type":"eq","fun":lambda x:np.sum(x)-1})

    weights = res.x

    # METRICS
    port_return = np.sum(returns.mean() * weights) * 252
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    sharpe = port_return / port_vol if port_vol != 0 else 0

    cumulative = (1 + returns.dot(weights)).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()

    # ==============================
    # DISPLAY
    # ==============================
    st.subheader("📊 Portfolio Metrics")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return", f"{port_return*100:.2f}%")
    c2.metric("Volatility", f"{port_vol*100:.2f}%")
    c3.metric("Sharpe", f"{sharpe:.2f}")
    c4.metric("Max Drawdown", f"{drawdown*100:.2f}%")

    # ==============================
    # RECOMMENDATION
    # ==============================
    st.subheader("📌 Recommendation")

    if sharpe > 1:
        st.success("Strong portfolio — good performance")
    elif sharpe > 0.5:
        st.warning("Average portfolio — can improve")
    else:
        st.error("Weak portfolio — rebalance needed")

    # ==============================
    # ALLOCATION
    # ==============================
    alloc = pd.DataFrame({
        "Stock": returns.columns,
        "Weight (%)": weights * 100,
        "Investment ₹": weights * investment
    }).sort_values(by="Weight (%)", ascending=False)

    st.subheader("📊 Allocation")
    st.bar_chart(alloc.set_index("Stock")["Weight (%)"])
    st.dataframe(alloc)

    # ==============================
    # GROWTH
    # ==============================
    st.subheader("📈 Portfolio Growth")
    st.line_chart(cumulative)

    # ==============================
    # 💾 SAVE TO DATABASE
    # ==============================
    if st.button("💾 Save Portfolio"):
    try:
        response = supabase.table("portfolios").insert({
            "username": st.session_state.user,
            "stocks": stocks_input
        }).execute()

        st.success("✅ Saved to Supabase!")

        st.write("DEBUG RESPONSE:", response)

    except Exception as e:
        st.error(f"❌ Error: {e}")

# ==============================
# 📁 LOAD SAVED PORTFOLIOS
# ==============================
st.subheader("📁 Your Saved Portfolios")

response = supabase.table("portfolios")\
    .select("*")\
    .eq("username", st.session_state.user)\
    .execute()

for row in response.data:
    st.write(f"• {row['stocks']}")
