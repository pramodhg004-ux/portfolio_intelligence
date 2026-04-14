import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import io

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Terminal", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= AUTO REFRESH =================
st_autorefresh(interval=30000, key="live_refresh")

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
            st.warning("Dev login used")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Terminal")
    st.subheader("Track • Analyze • Grow")
    st.stop()

user = st.session_state.user

# ================= NAV =================
page = st.sidebar.radio("Navigate", [
    "Terminal", "Analyze", "Portfolios"
])

# ================= TERMINAL =================
if page == "Terminal":

    st.title("💻 Trading Terminal")

    try:
        res = supabase.table("portfolios").select("*").eq("username", user).execute()
        count = len(res.data)
    except:
        count = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolios", count)
    c2.metric("Status", "LIVE")
    c3.metric("User", user)

    st.divider()

    st.subheader("📊 Market Snapshot")

    stocks = ["AAPL", "MSFT", "GOOGL"]

    data = yf.download(stocks, period="1d", interval="1m", progress=False)

    if data.empty:
        st.warning("Live data not available")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        st.line_chart(data)

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Portfolio Intelligence")

    stocks_input = st.text_input("Enter Stocks (any)", "AAPL,MSFT,GOOGL")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",")]

        valid_stocks = []
        price_data = {}

        # ===== FETCH DATA SAFELY =====
        for stock in stocks:
            try:
                temp = yf.download(stock, period="6mo", progress=False)

                if not temp.empty:
                    valid_stocks.append(stock)
                    price_data[stock] = temp["Close"]
            except:
                continue

        if not valid_stocks:
            st.error("No valid stocks found")
            st.stop()

        data = pd.DataFrame(price_data).dropna()

        if len(data) < 2:
            st.error("Not enough data")
            st.stop()

        latest = data.iloc[-1]
        prev = data.iloc[-2]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": valid_stocks})

        df["Invested"] = investment / len(valid_stocks)
        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Invested"] / df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]
        df["Return %"] = (df["P&L"] / df["Invested"]) * 100

        total_value = df["Value"].sum()
        pnl = total_value - investment

        # ===== METRICS =====
        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{investment:,.0f}")
        c2.metric("Value", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.divider()

        st.dataframe(df, use_container_width=True)

        # ===== SAVE HISTORY =====
        try:
            supabase.table("portfolio_history").insert({
                "username": user,
                "portfolio_name": "default",
                "date": pd.Timestamp.today().date().isoformat(),
                "value": float(total_value)
            }).execute()
        except:
            pass

        # ===== HISTORY CHART =====
        st.subheader("📊 Portfolio Growth")

        try:
            hist = supabase.table("portfolio_history") \
                .select("*") \
                .eq("username", user) \
                .execute()

            hist_df = pd.DataFrame(hist.data)

            if not hist_df.empty:
                hist_df["date"] = pd.to_datetime(hist_df["date"])
                hist_df = hist_df.sort_values("date")

                st.line_chart(hist_df.set_index("date")["value"])
        except:
            st.warning("No history data")

        # ===== DOWNLOAD =====
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button(
            label="📥 Download Portfolio",
            data=buffer,
            file_name="portfolio.xlsx",
            mime="application/vnd.ms-excel"
        )

# ================= PORTFOLIOS =================
elif page == "Portfolios":

    st.title("📁 Portfolios")

    name = st.text_input("Portfolio Name")
    stocks = st.text_area("Stocks")

    if st.button("Save Portfolio"):
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
        res = supabase.table("portfolios").select("*").eq("username", user).execute()

        for r in res.data:
            st.markdown(f"**{r['portfolio_name']}** → {r['stocks']}")
    except:
        st.warning("No portfolios found")
