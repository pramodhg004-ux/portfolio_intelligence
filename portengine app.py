import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Pro", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= LOGIN =================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Mode", ["Login", "Signup"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if mode == "Signup":
    if st.sidebar.button("Signup"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created. Now login.")
        except Exception as e:
            st.error(e)

if mode == "Login":
    if st.sidebar.button("Login"):
        try:
            supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = email
            st.rerun()
        except:
            st.error("Login failed")

if not st.session_state.user:
    st.title("🚀 Portfolio Intelligence Pro")
    st.subheader("Track • Analyze • Grow")
    st.stop()

user = st.session_state.user

# ================= CHECK PRO =================
def is_pro():
    try:
        res = supabase.table("subscriptions").select("*").eq("username", user).execute()
        return len(res.data) > 0
    except:
        return False

# ================= SIDEBAR =================
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Analyze", "Portfolios", "Upgrade"
])

# ================= DASHBOARD =================
if page == "Dashboard":

    st.title("📊 Dashboard")

    col1, col2 = st.columns(2)

    try:
        res = supabase.table("portfolios").select("*").eq("username", user).execute()
        count = len(res.data)
    except:
        count = 0

    col1.metric("Portfolios", count)
    col2.metric("Status", "PRO" if is_pro() else "Free")

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Portfolio Analyzer")

    stocks_input = st.text_input("Stocks (comma separated)", "AAPL,MSFT")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze", key="analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",")]

        data = yf.download(stocks, period="6mo", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        latest = data.iloc[-1]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": stocks})
        df["Investment"] = investment / len(stocks)
        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Investment"] / df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["PnL"] = df["Value"] - df["Investment"]

        total = df["Value"].sum()

        st.metric("Total Value", f"₹{total:,.0f}")
        st.dataframe(df)

        st.bar_chart(df.set_index("Stock")["Value"])

# ================= PORTFOLIOS =================
elif page == "Portfolios":

    st.title("📁 Your Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save", key="save_port"):
        try:
            supabase.table("portfolios").insert({
                "username": user,
                "portfolio_name": name,
                "stocks": stocks
            }).execute()
            st.success("Saved!")
        except Exception as e:
            st.error(e)

    try:
        res = supabase.table("portfolios").select("*").eq("username", user).execute()

        for p in res.data:
            st.card(f"{p['portfolio_name']} → {p['stocks']}")
    except:
        st.warning("No data")

# ================= UPGRADE =================
elif page == "Upgrade":

    st.title("💳 Upgrade")

    if is_pro():
        st.success("You are PRO")
    else:
        st.write("Unlock advanced analytics")

        st.markdown("""
        <a href="https://rzp.io/l/YOUR_LINK" target="_blank">
            <button style="padding:10px;background:#00b386;color:white;border:none;">
            Pay ₹499
            </button>
        </a>
        """, unsafe_allow_html=True)
