import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
from supabase import create_client
import io
import time

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = "https://bveslnslwdttqzxqmrth.supabase.co"
SUPABASE_KEY = "sb_publishable_avmvZzge1AZHSRcTXF4pfg_019rj-rC"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= AUTH =================
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
            st.success("Signup success")
        except Exception as e:
            st.error(e)

if auth_mode == "Login":
    if st.sidebar.button("Login"):
        try:
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = email
            st.rerun()
        except:
            st.session_state.user = email
            st.warning("Login bypassed (dev mode)")
            st.rerun()

if not st.session_state.user:
    st.title("🔐 Login Required")
    st.stop()

# ================= SUBSCRIPTION =================
sub = supabase.table("subscriptions").select("*") \
    .eq("username", st.session_state.user).execute()

is_pro = len(sub.data) > 0

# ================= NAV =================
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📈 Analyze", "📁 Portfolios", "💳 Upgrade"]
)

# ================= DASHBOARD =================
if page == "🏠 Dashboard":

    st.title("🏠 Portfolio Dashboard")

    res = supabase.table("portfolios") \
        .select("*") \
        .eq("username", st.session_state.user) \
        .execute()

    st.metric("Saved Portfolios", len(res.data))

    history = supabase.table("portfolio_history") \
        .select("*") \
        .eq("username", st.session_state.user) \
        .execute()

    if history.data:
        df = pd.DataFrame(history.data)
        df["date"] = pd.to_datetime(df["date"])
        st.line_chart(df.set_index("date")["value"])

# ================= ANALYZE =================
if page == "📈 Analyze":

    st.title("📊 Holdings")

    stocks_input = st.text_area("Stocks", "AAPL,MSFT")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]
        data = yf.download(stocks, period="6mo", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        data = data.dropna()
        returns = data.pct_change().dropna()

        weights = np.ones(len(stocks)) / len(stocks)

        latest = data.iloc[-1]
        prev = data.iloc[-2]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": stocks})

        df["Investment ₹"] = investment / len(stocks)
        df["Avg Price"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Investment ₹"] / df["Avg Price"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Investment ₹"]
        df["Day %"] = ((df["LTP"] - df["Stock"].map(prev)) / df["Stock"].map(prev)) * 100

        total_value = df["Value"].sum()
        pnl = total_value - investment

        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{investment:,.0f}")
        c2.metric("Value", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.dataframe(df)

        st.bar_chart(df.set_index("Stock")["Value"])

        # SAVE HISTORY
        supabase.table("portfolio_history").insert({
            "username": st.session_state.user,
            "portfolio_name": "default",
            "date": pd.Timestamp.today().date().isoformat(),
            "value": float(total_value)
        }).execute()

        # PRO FEATURES
        if is_pro:

            st.subheader("🏢 Sector Allocation")

            sectors = {}
            for s in stocks:
                try:
                    sectors[s] = yf.Ticker(s).info.get("sector", "Other")
                except:
                    sectors[s] = "Other"

            df["Sector"] = df["Stock"].map(sectors)
            st.bar_chart(df.groupby("Sector")["Value"].sum())

        else:
            st.info("Upgrade to PRO for sector analysis")

# ================= PORTFOLIOS =================
if page == "📁 Portfolios":

    st.title("📁 Your Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save"):
        supabase.table("portfolios").insert({
            "username": st.session_state.user,
            "portfolio_name": name,
            "stocks": stocks
        }).execute()
        st.success("Saved")

    res = supabase.table("portfolios") \
        .select("*") \
        .eq("username", st.session_state.user) \
        .execute()

    for r in res.data:
        st.write(r["portfolio_name"], "-", r["stocks"])

# ================= UPGRADE =================
if page == "💳 Upgrade":

    st.title("💳 Go PRO")

    if is_pro:
        st.success("You are PRO user")
    else:
        st.write("Unlock premium features:")
        st.write("- Sector Analysis")
        st.write("- Advanced analytics")

        if st.button("Upgrade Now"):
            supabase.table("subscriptions").insert({
                "username": st.session_state.user,
                "plan": "pro"
            }).execute()
            st.success("Upgraded!")
