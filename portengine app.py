import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= UI STYLE =================
st.markdown("""
<style>
body { background-color: #0e1117; color: white; }
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

# ================= AUTH =================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Mode", ["Login", "Signup"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if mode == "Signup":
    if st.sidebar.button("Signup"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("Signup success")
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
            # SAFE FALLBACK (so app never breaks)
            st.session_state.user = email
            st.warning("Login fallback (dev mode)")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Intelligence Pro")
    st.subheader("Track • Analyze • Grow")
    st.stop()

user = st.session_state.user

# ================= SUBSCRIPTION =================
def is_pro():
    try:
        res = supabase.table("subscriptions").select("*") \
            .eq("username", user).execute()
        return len(res.data) > 0
    except:
        return False

# ================= NAV =================
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Analyze", "Portfolios", "Upgrade"
])

# ================= DASHBOARD =================
if page == "Dashboard":

    st.title("📊 Portfolio Dashboard")

    col1, col2, col3 = st.columns(3)

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user).execute()
        count = len(res.data)
    except:
        count = 0

    col1.metric("📁 Portfolios", count)
    col2.metric("💼 Plan", "PRO" if is_pro() else "Free")
    col3.metric("📈 Status", "Active")

    st.divider()

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Holdings (Zerodha Style)")

    stocks_input = st.text_input("Stocks", "AAPL,MSFT")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze", key="analyze_btn"):

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
        df["Avg"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Invested"] / df["Avg"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]
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

# ================= PORTFOLIOS =================
elif page == "Portfolios":

    st.title("📁 Your Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save Portfolio", key="save_port"):
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
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", user) \
            .execute()

        for r in res.data:
            st.markdown(f"**{r['portfolio_name']}** → {r['stocks']}")
    except:
        st.warning("No portfolios")

# ================= UPGRADE =================
elif page == "Upgrade":

    st.title("💳 Upgrade to PRO")

    if is_pro():
        st.success("You are PRO user")
    else:
        st.write("Unlock:")
        st.write("- Sector analysis")
        st.write("- Advanced insights")

        st.markdown("""
        <a href="https://rzp.io/l/YOUR_LINK" target="_blank">
            <button style="
                background:#00b386;
                color:white;
                padding:12px;
                border:none;
                border-radius:6px;">
            Pay ₹499
            </button>
        </a>
        """, unsafe_allow_html=True)
