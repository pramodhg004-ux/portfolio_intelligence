import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import io
import requests

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Terminal Pro", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= AUTO REFRESH =================
st_autorefresh(interval=3000, key="live_refresh")

# ================= STYLE =================
st.markdown("""
<style>
body {background-color:#0b0f1a;color:#e6e6e6;}
.card {background:#111827;padding:15px;border-radius:10px;}
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
            st.session_state.user = email
            st.warning("Dev login")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Terminal Pro")
    st.stop()

user = st.session_state.user

# ================= NAV =================
page = st.sidebar.radio("Navigate", ["Terminal", "Analyze", "Portfolios"])

# ================= TERMINAL =================
if page == "Terminal":

    st.title("💻 Live Trading Terminal")

    watchlist = st.text_input(
        "Watchlist",
        "AAPL,MSFT,TSLA"
    )

    stocks = [s.strip().upper() for s in watchlist.split(",")]
    api_key = st.secrets["FINNHUB_API_KEY"]

    data_rows = []

    for stock in stocks:
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={stock}&token={api_key}"
            r = requests.get(url).json()

            if r and "c" in r and r["c"] != 0:
                price = r["c"]
                prev_close = r["pc"]

                change = ((price - prev_close) / prev_close) * 100

                data_rows.append({
                    "Stock": stock,
                    "Price": price,
                    "Change %": change
                })

        except:
            continue

    if not data_rows:
        st.warning("No data fetched")
    else:
        df = pd.DataFrame(data_rows)

        cols = st.columns(len(df))

        for i, row in df.iterrows():
            color = "green" if row["Change %"] > 0 else "red"

            cols[i].markdown(f"""
            <div class="card">
            <h4>{row['Stock']}</h4>
            <h2>{row['Price']:.2f}</h2>
            <p style="color:{color}">{row['Change %']:.2f}%</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.dataframe(df, use_container_width=True)

elif page == "Analyze":

    st.title("📈 Portfolio Intelligence")

    st.markdown("### Enter Stocks with Allocation %")
    st.markdown("Example: AAPL:40, MSFT:30, TSLA:30")

    stocks_input = st.text_input("Stocks + Allocation", "AAPL:40,MSFT:30,TSLA:30")
    investment = st.number_input("Total Investment ₹", value=100000)

    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False

    if st.button("Analyze"):
        st.session_state.analysis_done = True

        items = [s.strip() for s in stocks_input.split(",")]

        stocks = []
        allocation = {}

        for item in items:
            try:
                stock, pct = item.split(":")
                stock = stock.upper()
                pct = float(pct)

                stocks.append(stock)
                allocation[stock] = pct
            except:
                continue

        price_data = {}
        valid = []

        for stock in stocks:
            try:
                temp = yf.download(stock, period="6mo", progress=False)

                if not temp.empty:
                    price_data[stock] = temp["Close"]
                    valid.append(stock)
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

        df["Allocation %"] = df["Stock"].map(allocation)

        df["Invested"] = (df["Allocation %"] / 100) * investment

        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Qty"] = df["Invested"] / df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]
        df["Return %"] = (df["P&L"] / df["Invested"]) * 100

        st.session_state.result_df = df

    # ===== SHOW RESULT (PERSISTENT) =====
    if st.session_state.analysis_done:

        df = st.session_state.result_df

        total_invested = df["Invested"].sum()
        total_value = df["Value"].sum()
        pnl = total_value - total_invested

        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", f"₹{total_invested:,.0f}")
        c2.metric("Value", f"₹{total_value:,.0f}")
        c3.metric("P&L", f"₹{pnl:,.0f}")

        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button(
            "📥 Download Portfolio",
            buffer,
            "portfolio.xlsx"
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
