import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= TEMP USER =================
user = "demo_user"

# ================= SIDEBAR =================
st.sidebar.title("📊 Menu")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📈 Analyze", "📁 Portfolios", "💳 Upgrade"]
)

# ================= DASHBOARD =================
if page == "🏠 Dashboard":

    st.title("🚀 Portfolio Intelligence Pro")
    st.subheader("Track. Analyze. Grow your wealth.")

# ================= ANALYZE =================
elif page == "📈 Analyze":

    st.title("📊 Holdings Dashboard")

    stocks_input = st.text_area("Stocks", "AAPL,MSFT")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

        data = yf.download(stocks, period="6mo", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        data = data.dropna()

        latest = data.iloc[-1]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": stocks})

        df["Investment ₹"] = investment / len(stocks)
        df["Avg Price"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Investment ₹"] / df["Avg Price"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Investment ₹"]

        st.dataframe(df)

# ================= PORTFOLIOS =================
elif page == "📁 Portfolios":

    st.title("📁 Your Portfolios")

    if st.button("Save Demo Portfolio"):
        supabase.table("portfolios").insert({
            "username": user,
            "portfolio_name": "Demo",
            "stocks": "AAPL,MSFT"
        }).execute()

        st.success("Saved!")

# ================= UPGRADE =================
elif page == "💳 Upgrade":

    st.title("💳 Upgrade")

    st.markdown("""
    <a href="https://rzp.io/l/YOUR_LINK" target="_blank">
        <button>Pay ₹499</button>
    </a>
    """, unsafe_allow_html=True)
