import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import io

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Terminal Pro", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= BLOOMBERG STYLE =================
st.markdown("""
<style>
body {
    background-color: #0b0f1a;
    color: #e6e6e6;
}
.metric-card {
    background-color: #111827;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ================= AUTO REFRESH =================
st_autorefresh(interval=2000, key="live_refresh")  # 2 sec refresh

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
            st.session_state.user = email
            st.warning("Dev login")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Terminal Pro")
    st.stop()

user = st.session_state.user

# ================= HELPERS =================
def format_stock(symbol):
    symbol = symbol.upper().strip()
    if "." in symbol or "-" in symbol:
        return symbol
    return symbol + ".NS" if len(symbol) <= 6 else symbol

# ================= NAV =================
page = st.sidebar.radio("Navigate", [
    "Terminal", "Analyze", "Portfolios"
])

# ================= TERMINAL =================
if page == "Terminal":

    st.title("💻 Bloomberg Terminal")

    watchlist = st.text_input(
        "Watchlist",
        "AAPL,MSFT,RELIANCE,TCS"
    )

    stocks = [format_stock(s.strip()) for s in watchlist.split(",")]

    price_data = {}
    valid = []

    for s in stocks:
        try:
            temp = yf.download(s, period="1d", interval="1m", progress=False)

            if not temp.empty:
                price_data[s] = temp["Close"]
                valid.append(s)
        except:
            continue

    if not price_data:
        st.warning("No valid data")
    else:
        data = pd.concat(price_data.values(), axis=1)
        data.columns = valid
        data = data.dropna()

        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # ===== TERMINAL GRID =====
        cols = st.columns(len(valid))

        for i, stock in enumerate(valid):
            price = latest[stock]
            change = ((latest[stock] - prev[stock]) / prev[stock]) * 100

            color = "green" if change > 0 else "red"

            cols[i].markdown(f"""
            <div class="metric-card">
            <h4>{stock}</h4>
            <h2>₹{price:.2f}</h2>
            <p style="color:{color}">{change:.2f}%</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        st.subheader("📊 Live Chart")
        st.line_chart(data)

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Portfolio Intelligence")

    stocks_input = st.text_input("Stocks", "AAPL,RELIANCE,TCS")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze"):

        stocks = [format_stock(s.strip()) for s in stocks_input.split(",")]

        price_data = {}
        valid = []

        for s in stocks:
            try:
                temp = yf.download(s, period="6mo", progress=False)

                if not temp.empty:
                    price_data[s] = temp["Close"]
                    valid.append(s)
            except:
                continue

        if not price_data:
            st.error("No valid stocks")
            st.stop()

        data = pd.concat(price_data.values(), axis=1)
        data.columns = valid
        data = data.dropna()

        latest = data.iloc[-1]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": valid})

        df["Invested"] = investment / len(valid)
        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Invested"] / df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]

        total_value = df["Value"].sum()
        pnl = total_value - investment

        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{investment:,.0f}")
        c2.metric("Value", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.dataframe(df)

        # ===== DOWNLOAD =====
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button("Download", buffer, "portfolio.xlsx")

# ================= PORTFOLIOS =================
elif page == "Portfolios":

    st.title("📁 Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save"):
        try:
            supabase.table("portfolios").insert({
                "username": user,
                "portfolio_name": name,
                "stocks": stocks
            }).execute()
            st.success("Saved")
        except Exception as e:
            st.error(e)
