import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
from supabase import create_client
import io
import time

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

SUPABASE_URL = "https://bveslnslwdttqzxqmrth.supabase.co"
SUPABASE_KEY = "sb_publishable_avmvZzge1AZHSRcTXF4pfg_019rj-rC"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# AUTH
# ==============================
st.sidebar.title("🔐 Account")

auth_mode = st.sidebar.radio("Choose", ["Login", "Signup"])

email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if "user" not in st.session_state:
    st.session_state.user = None

# SIGNUP
if auth_mode == "Signup":
    if st.sidebar.button("Create Account"):
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            st.success("Signup successful! Now login.")
        except Exception as e:
            st.error(f"Signup failed: {e}")

# LOGIN (bypass confirmation)
if auth_mode == "Login":
    if st.sidebar.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            st.session_state.user = email
            st.success("Logged in!")
            st.rerun()

        except Exception as e:
            if "Email not confirmed" in str(e):
                st.session_state.user = email
                st.warning("Logged in without verification")
                st.rerun()
            else:
                st.error(f"Login failed: {e}")

if st.session_state.user is None:
    st.title("🔐 Please Login")
    st.stop()

# ==============================
# SIDEBAR NAV
# ==============================
st.sidebar.title("📊 Dashboard")

page = st.sidebar.radio(
    "Navigate",
    ["📈 Analyze", "📁 Saved Portfolios", "⚙️ Settings"]
)

# ==============================
# ANALYZE PAGE
# ==============================
if page == "📈 Analyze":

    st.title("🚀 Portfolio Intelligence Pro")

    # LOAD SAVED
    load_option = st.checkbox("📂 Load saved portfolio")

    stocks_input = "AAPL,MSFT,GOOGL"

    if load_option:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", st.session_state.user) \
            .execute()

        if res.data:
            names = [r["portfolio_name"] for r in res.data]
            selected = st.selectbox("Choose portfolio", names)
            selected_data = next(r for r in res.data if r["portfolio_name"] == selected)
            stocks_input = selected_data["stocks"]

    stocks_input = st.text_area("Stocks", stocks_input)

    portfolio_name = st.text_input("Portfolio Name")
    investment = st.number_input("Investment ₹", value=100000)

    auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)

    if st.button("Analyze Portfolio") or auto_refresh:

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

        data = yf.download(stocks, period="1y", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        data = data.dropna()
        returns = data.pct_change().dropna()

        if returns.empty:
            st.error("No data available")
            st.stop()

        # OPTIMIZATION
        def neg_sharpe(w):
            r = np.sum(returns.mean() * w) * 252
            v = np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            return -r / v

        n = len(returns.columns)
        w0 = np.ones(n) / n

        res = minimize(
            neg_sharpe,
            w0,
            bounds=[(0, 1)] * n,
            constraints={"type": "eq", "fun": lambda x: np.sum(x) - 1},
        )

        weights = res.x

        port_return = np.sum(returns.mean() * weights) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        sharpe = port_return / port_vol if port_vol != 0 else 0

        cumulative = (1 + returns.dot(weights)).cumprod()
        drawdown = (cumulative / cumulative.cummax() - 1).min()

        # METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return", f"{port_return*100:.2f}%")
        c2.metric("Volatility", f"{port_vol*100:.2f}%")
        c3.metric("Sharpe", f"{sharpe:.2f}")
        c4.metric("Drawdown", f"{drawdown*100:.2f}%")

        # AI INSIGHTS
        st.subheader("🤖 AI Insights")

        if sharpe > 1.2:
            st.success("Excellent portfolio")
        elif sharpe > 0.7:
            st.warning("Moderate performance")
        else:
            st.error("Poor portfolio")

        if drawdown < -0.3:
            st.warning("High risk detected")

        # TABLE
        latest_prices = data.iloc[-1]
        buy_prices = data.iloc[0]

        alloc = pd.DataFrame({
            "Stock": returns.columns,
            "Weight (%)": weights * 100
        })

        alloc["Investment ₹"] = alloc["Weight (%)"] / 100 * investment
        alloc["Buy Price"] = alloc["Stock"].map(buy_prices)
        alloc["Current Price"] = alloc["Stock"].map(latest_prices)

        alloc["Quantity"] = alloc["Investment ₹"] / alloc["Buy Price"]
        alloc["Value ₹"] = alloc["Quantity"] * alloc["Current Price"]
        alloc["P&L ₹"] = alloc["Value ₹"] - alloc["Investment ₹"]

        st.subheader("📊 Portfolio Breakdown")
        st.dataframe(alloc)

        st.subheader("📈 Portfolio Growth")
        st.line_chart(cumulative)
        # ==============================
# SAVE DAILY PERFORMANCE
# ==============================
try:
    today_value = float(cumulative.iloc[-1] * investment)

    supabase.table("portfolio_history").insert({
        "username": st.session_state.user,
        "portfolio_name": portfolio_name,
        "date": pd.Timestamp.today().date().isoformat(),
        "value": today_value
    }).execute()

except:
    pass

        # DOWNLOAD
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            alloc.to_excel(writer, sheet_name='Portfolio', index=False)
            cumulative.to_frame(name="Growth").to_excel(writer, sheet_name='Performance')

        buffer.seek(0)

        st.download_button(
            label="📥 Download Report",
            data=buffer,
            file_name="portfolio_report.xlsx"
        )

        # SAVE
        if st.button("💾 Save Portfolio"):
            try:
                supabase.table("portfolios").insert({
                    "username": st.session_state.user,
                    "portfolio_name": portfolio_name,
                    "stocks": stocks_input
                }).execute()
                st.success("Saved successfully!")
            except Exception as e:
                st.error(e)

        # AUTO REFRESH
        if auto_refresh:
            time.sleep(10)
            st.rerun()

# ==============================
# SAVED PORTFOLIOS
# ==============================
if page == "📁 Saved Portfolios":

    st.title("📁 Your Portfolios")

    try:
        res = supabase.table("portfolios") \
            .select("*") \
            .eq("username", st.session_state.user) \
            .order("created_at", desc=True) \
            .execute()

        if res.data:
            names = [r["portfolio_name"] for r in res.data]

            selected = st.selectbox("Select Portfolio", names)

            selected_data = next(r for r in res.data if r["portfolio_name"] == selected)

            st.write("📌 Stocks:", selected_data["stocks"])
            st.write("📅 Created:", selected_data["created_at"])

        else:
            st.info("No portfolios yet")

    except Exception as e:
        st.error(e)
st.subheader("📈 Portfolio Performance History")

history = supabase.table("portfolio_history") \
    .select("*") \
    .eq("username", st.session_state.user) \
    .eq("portfolio_name", selected) \
    .order("date") \
    .execute()

if history.data:
    df = pd.DataFrame(history.data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    st.line_chart(df.set_index("date")["value"])
# ==============================
# SETTINGS
# ==============================
if page == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.write("Coming soon...")
