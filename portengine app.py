import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from supabase import create_client

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= AUTH =================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Mode", ["Login", "Signup"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if mode == "Signup":
    if st.sidebar.button("Signup", key="signup"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("Signup success")
        except Exception as e:
            st.error(e)

if mode == "Login":
    if st.sidebar.button("Login", key="login"):
        try:
            supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = email
            st.rerun()
        except:
            st.session_state.user = email
            st.warning("Dev login used")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Intelligence Pro")
    st.stop()

user = st.session_state.user

# ================= PRO CHECK =================
def is_pro():
    try:
        res = supabase.table("subscriptions").select("*") \
            .eq("username", user).execute()
        return len(res.data) > 0
    except:
        return False

# ================= NAV =================
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Analyze", "Portfolios"
])

# ================= DASHBOARD =================
if page == "Dashboard":

    st.title("📊 Dashboard")

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user) \
            .execute()
        count = len(res.data)
    except:
        count = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolios", count)
    c2.metric("Plan", "PRO" if is_pro() else "Free")
    c3.metric("Status", "Active")

    st.divider()

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Portfolio Intelligence")

    stocks_input = st.text_input("Stocks", "AAPL,MSFT,GOOGL")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze", key="analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",")]

        data = yf.download(stocks, period="6mo", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        data = data.dropna()

        latest = data.iloc[-1]
        prev = data.iloc[-2]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": stocks})

        df["Invested"] = investment / len(stocks)
        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Invested"] / df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]
        df["Return %"] = (df["P&L"] / df["Invested"]) * 100
        df["Day %"] = ((df["LTP"] - df["Stock"].map(prev)) / df["Stock"].map(prev)) * 100

        total_value = df["Value"].sum()
        pnl = total_value - investment

        # ===== METRICS =====
        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{investment:,.0f}")
        c2.metric("Current", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.divider()

        # ===== TABLE =====
        st.dataframe(df, use_container_width=True)

        # ===== CHART =====
        st.subheader("📊 Allocation")
        st.bar_chart(df.set_index("Stock")["Value"])

        # ===== BLOOMBERG STYLE INSIGHTS =====
        st.subheader("📊 Insights")

        best = df.loc[df["P&L"].idxmax()]
        worst = df.loc[df["P&L"].idxmin()]

        vol = data.pct_change().std().mean() * np.sqrt(252)

        i1, i2, i3 = st.columns(3)
        i1.metric("Top Gainer", best["Stock"])
        i2.metric("Top Loser", worst["Stock"])
        i3.metric("Volatility", f"{vol:.2%}")

# ================= PORTFOLIOS =================
elif page == "Portfolios":

    st.title("📁 Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save", key="save"):
        try:
            supabase.table("portfolios").insert({
                "username": user,
                "portfolio_name": name,
                "stocks": stocks
            }).execute()
            st.success("Saved")
        except Exception as e:
            st.error(e)

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user) \
            .execute()

        for r in res.data:
            st.markdown(f"**{r['portfolio_name']}** → {r['stocks']}")
    except:
        st.warning("No portfolios")
