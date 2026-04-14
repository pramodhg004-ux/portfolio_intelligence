import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
from supabase import create_client
import io
import time

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = "https://bveslnslwdttqzxqmrth.supabase.co"
SUPABASE_KEY = "sb_publishable_avmvZzge1AZHSRcTXF4pfg_019rj-rC"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# AUTH SYSTEM
# ==============================
st.sidebar.title("🔐 Account")

auth_mode = st.sidebar.radio("Choose", ["Login", "Signup"])

email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if "user" not in st.session_state:
    st.session_state.user = None

if auth_mode == "Signup":
    if st.sidebar.button("Create Account"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created! Now login.")
        except Exception as e:
            st.error(e)

if auth_mode == "Login":
    if st.sidebar.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = res.user.email
            st.success("Logged in!")
        except Exception as e:
            st.error("Login failed")

if st.session_state.user is None:
    st.title("🔐 Please Login")
    st.stop()

# ==============================
# SIDEBAR NAV
# ==============================
st.sidebar.title("📊 Dashboard")

page = st.sidebar.radio(
    "Navigate",
    ["📈 Analyze", "📁 Saved", "⚙️ Settings"]
)

# ==============================
# ANALYZE PAGE
# ==============================
if page == "📈 Analyze":

    st.title(f"🚀 Portfolio Intelligence Pro")

    stocks_input = st.text_area("Stocks", "AAPL,MSFT,GOOGL")
    investment = st.number_input("Investment ₹", value=100000)

    auto_refresh = st.checkbox("🔄 Auto Refresh (live market)", value=False)

    if st.button("Analyze Portfolio") or auto_refresh:

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

        data = yf.download(stocks, period="1y", interval="1d", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        returns = data.pct_change().dropna()

        def neg_sharpe(w):
            r = np.sum(returns.mean() * w) * 252
            v = np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            return -r / v

        n = len(returns.columns)
        w0 = np.ones(n) / n

        res = minimize(
            neg_sharpe,
            w0,
            bounds=[(0, 1)] * n,
            constraints={"type": "eq", "fun": lambda x: np.sum(x) - 1},
        )

        weights = res.x

        port_return = np.sum(returns.mean() * weights) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        sharpe = port_return / port_vol if port_vol != 0 else 0

        cumulative = (1 + returns.dot(weights)).cumprod()
        drawdown = (cumulative / cumulative.cummax() - 1).min()

        # KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return", f"{port_return*100:.2f}%")
        c2.metric("Volatility", f"{port_vol*100:.2f}%")
        c3.metric("Sharpe", f"{sharpe:.2f}")
        c4.metric("Drawdown", f"{drawdown*100:.2f}%")

        # ==============================
        # AI RECOMMENDATION
        # ==============================
        st.subheader("🤖 AI Recommendation")

        if sharpe > 1.2:
            st.success("Excellent portfolio — maintain allocation")
        elif sharpe > 0.7:
            st.warning("Moderate — consider diversification")
        else:
            st.error("Poor performance — rebalance required")

        if drawdown < -0.3:
            st.warning("High drawdown — reduce risk exposure")

        # ==============================
        # ALLOCATION
        # ==============================
        latest_prices = data.iloc[-1]
        buy_prices = data.iloc[0]

        alloc = pd.DataFrame({
            "Stock": returns.columns,
            "Weight (%)": weights * 100
        })

        alloc["Investment ₹"] = alloc["Weight (%)"] / 100 * investment
        alloc["Buy Price"] = alloc["Stock"].map(buy_prices)
        alloc["Current Price"] = alloc["Stock"].map(latest_prices)

        alloc["Quantity"] = alloc["Investment ₹"] / alloc["Buy Price"]
        alloc["Value ₹"] = alloc["Quantity"] * alloc["Current Price"]
        alloc["P&L ₹"] = alloc["Value ₹"] - alloc["Investment ₹"]

        st.dataframe(alloc)

        st.line_chart(cumulative)

        # ==============================
        # SAVE
        # ==============================
        if st.button("💾 Save Portfolio"):
            supabase.table("portfolios").insert({
                "username": st.session_state.user,
                "stocks": stocks_input
            }).execute()
            st.success("Saved!")

        # AUTO REFRESH
        if auto_refresh:
            time.sleep(10)
            st.rerun()

# ==============================
# SAVED
# ==============================
if page == "📁 Saved":

    st.title("Saved Portfolios")

    res = supabase.table("portfolios") \
        .select("*") \
        .eq("username", st.session_state.user) \
        .execute()

    for r in res.data:
        st.write(r["stocks"])

# ==============================
# SETTINGS
# ==============================
if page == "⚙️ Settings":
    st.title("Settings")
    st.write("Coming soon...")
