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

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= AUTH PAGE =================
if st.session_state.user is None:

    st.title("🚀 Portfolio Intelligence Pro")
    st.subheader("Track. Analyze. Grow your wealth.")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    if col1.button("Login"):
        try:
            supabase.auth.sign_in_with_password({
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
            st.success("Signup successful")
        except:
            st.error("Signup failed")

    st.stop()

# ================= USER =================
user = st.session_state.user

# ================= SUBSCRIPTION =================
def is_pro_user():
    try:
        res = supabase.table("subscriptions") \
            .select("*") \
            .eq("username", user) \
            .execute()
        return len(res.data) > 0
    except:
        return False

is_pro = is_pro_user()

# ================= SIDEBAR =================
st.sidebar.title("📊 Menu")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📈 Analyze", "📁 Portfolios", "💳 Upgrade"]
)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ================= DASHBOARD =================
if page == "🏠 Dashboard":

    st.title(f"👋 Welcome {user}")

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user) \
            .execute()

        st.metric("Saved Portfolios", len(res.data))

    except:
        st.warning("Database issue")

# ================= ANALYZE =================
elif page == "📈 Analyze":

    st.title("📊 Holdings Dashboard")

    stocks_input = st.text_area("Stocks (comma separated)", "AAPL,MSFT")
    investment = st.number_input("Total Investment ₹", value=100000)

    if st.button("Analyze Portfolio"):

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

        try:
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

            df["Quantity"] = df["Investment ₹"] / df["Avg Price"]
            df["Current Value"] = df["Quantity"] * df["LTP"]
            df["P&L"] = df["Current Value"] - df["Investment ₹"]
            df["Day %"] = ((df["LTP"] - df["Stock"].map(prev)) / df["Stock"].map(prev)) * 100

            total_value = df["Current Value"].sum()
            pnl = total_value - investment

            c1, c2, c3 = st.columns(3)
            c1.metric("Invested", f"₹{investment:,.0f}")
            c2.metric("Current Value", f"₹{total_value:,.0f}")
            c3.metric("P&L", f"₹{pnl:,.0f}")

            st.subheader("📋 Holdings")
            st.dataframe(df)

            st.subheader("📊 Allocation")
            st.bar_chart(df.set_index("Stock")["Current Value"])

            # SAVE
            st.divider()
            st.subheader("💾 Save Portfolio")

            name = st.text_input("Portfolio Name")

            if st.button("Save Portfolio"):
                try:
                    supabase.table("portfolios").insert({
                        "username": user,
                        "portfolio_name": name,
                        "stocks": stocks_input
                    }).execute()
                    st.success("Saved successfully")
                except:
                    st.error("Save failed")

            # PRO FEATURE
            if is_pro:
                st.divider()
                st.subheader("🏢 Sector Allocation")

                sectors = {}
                for s in stocks:
                    try:
                        sectors[s] = yf.Ticker(s).info.get("sector", "Other")
                    except:
                        sectors[s] = "Other"

                df["Sector"] = df["Stock"].map(sectors)
                st.bar_chart(df.groupby("Sector")["Current Value"].sum())

            else:
                st.warning("Upgrade to PRO for sector insights")

        except:
            st.error("Stock data error")

# ================= PORTFOLIOS =================
elif page == "📁 Portfolios":

    st.title("📁 Your Portfolios")

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user) \
            .execute()

        if res.data:
            for r in res.data:
                st.write(f"📌 {r['portfolio_name']} → {r['stocks']}")
        else:
            st.info("No portfolios yet")

    except:
        st.error("Error loading data")

# ================= UPGRADE =================
elif page == "💳 Upgrade":

    st.title("💳 Upgrade to PRO")

    if is_pro:
        st.success("You are already PRO")
    else:
        st.write("Unlock:")
        st.write("- Sector analysis")
        st.write("- Advanced insights")

        st.markdown("""
        <a href="https://rzp.io/l/YOUR_LINK" target="_blank">
            <button style="
                background:#3399cc;
                color:white;
                padding:12px 20px;
                border:none;
                border-radius:6px;
                font-size:16px;">
            Pay ₹499
            </button>
        </a>
        """, unsafe_allow_html=True)
