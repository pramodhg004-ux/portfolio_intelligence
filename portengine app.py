import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from supabase import create_client

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LANDING =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:

    st.title("🚀 Portfolio Intelligence Pro")

    st.subheader("Track. Analyze. Grow your wealth.")

    st.markdown("""
    ### Why this app?
    - 📊 Real-time portfolio tracking  
    - 📈 AI insights  
    - 🏢 Sector analysis  
    - 🔔 Alerts  

    ### Pricing:
    - Free → Basic tracking  
    - PRO → ₹499/month  
    """)

    st.divider()

    st.subheader("Login / Signup")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    if col1.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = email
            st.rerun()
        except:
            st.error("Login failed")

    if col2.button("Signup"):
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            st.success("Signup success")
        except:
            st.error("Signup failed")

    st.stop()

# ================= USER =================
user = st.session_state.user

sub = supabase.table("subscriptions").select("*") \
    .eq("username", user).execute()

is_pro = len(sub.data) > 0

# ================= NAV =================
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📈 Analyze", "📁 Portfolios", "💳 Upgrade"]
)

# LOGOUT
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ================= DASHBOARD =================
if page == "🏠 Dashboard":

    st.title(f"Welcome {user}")

    res = supabase.table("portfolios") \
        .select("*") \
        .eq("username", user).execute()

    st.metric("Portfolios", len(res.data))

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

        total_value = df["Value"].sum()

        st.metric("Portfolio Value", f"₹{total_value:,.0f}")

        st.dataframe(df)

        # PRO FEATURE
        if is_pro:
            st.subheader("Sector Analysis")

            sectors = {}
            for s in stocks:
                try:
                    sectors[s] = yf.Ticker(s).info.get("sector", "Other")
                except:
                    sectors[s] = "Other"

            df["Sector"] = df["Stock"].map(sectors)
            st.bar_chart(df.groupby("Sector")["Value"].sum())

        else:
            st.warning("Upgrade to PRO")

# ================= PORTFOLIOS =================
if page == "📁 Portfolios":

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save"):
        supabase.table("portfolios").insert({
            "username": user,
            "portfolio_name": name,
            "stocks": stocks
        }).execute()

    res = supabase.table("portfolios") \
        .select("*") \
        .eq("username", user).execute()

    for r in res.data:
        st.write(r["portfolio_name"], "-", r["stocks"])

# ================= UPGRADE =================
if page == "💳 Upgrade":

    st.title("Upgrade to PRO")

    st.markdown("""
    <a href="https://rzp.io/l/YOUR_LINK" target="_blank">
        <button style="background:#3399cc;color:white;padding:10px;">
        Pay ₹499
        </button>
    </a>
    """, unsafe_allow_html=True)

    st.info("Payment auto-activates PRO (no button needed)")
