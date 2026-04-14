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
    st.stop()

user = st.session_state.user

# ================= NAV =================
page = st.sidebar.radio("Navigate", [
    "Terminal", "Analyze", "Portfolios"
])

# ================= TERMINAL =================
if page == "Terminal":

    st.title("💻 Trading Terminal")

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

    stocks_input = st.text_input("Stocks", "AAPL,MSFT,GOOGL")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze"):

        stocks = [s.strip().upper() for s in stocks_input.split(",")]

        price_data = {}
        valid_stocks = []

        for stock in stocks:
            try:
                temp = yf.download(stock, period="6mo", progress=False)

                if not temp.empty and "Close" in temp:
                    series = temp["Close"].dropna()

                    if len(series) > 2:
                        price_data[stock] = series
                        valid_stocks.append(stock)

            except:
                continue

        # ===== SAFETY CHECK =====
        if not price_data:
            st.error("No valid stock data found")
            st.stop()

        # ===== SAFE DATAFRAME CREATION =====
        try:
            data = pd.concat(price_data.values(), axis=1)
            data.columns = valid_stocks
            data = data.dropna()
        except:
            st.error("Data processing failed")
            st.stop()

        if len(data) < 2:
            st.error("Not enough data to analyze")
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

        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{investment:,.0f}")
        c2.metric("Value", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.dataframe(df, use_container_width=True)

        # ===== DOWNLOAD =====
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button(
            "📥 Download Portfolio",
            data=buffer,
            file_name="portfolio.xlsx"
        )

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
