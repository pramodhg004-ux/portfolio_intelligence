import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy.optimize import minimize
from supabase import create_client
import io

# ==============================
# 🎨 PAGE CONFIG
# ==============================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

st.markdown("""
<style>
body {
    background-color: #0e1117;
}
.metric-card {
    background-color: #161b22;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# 🔑 SUPABASE CONFIG
# ==============================
SUPABASE_URL = "https://bveslnslwdttqzxqmrth.supabase.co"
SUPABASE_KEY = "sb_publishable_avmvZzge1AZHSRcTXF4pfg_019rj-rC"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# 🔐 LOGIN
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 Login")
    username = st.text_input("Enter Username")

    if st.button("Login"):
        if username:
            st.session_state.user = username
            st.rerun()

    st.stop()

# ==============================
# 📂 SIDEBAR
# ==============================
st.sidebar.title("📊 Dashboard")

page = st.sidebar.radio(
    "Navigate",
    ["📈 Analyze", "📁 Saved Portfolios", "⚙️ Settings"]
)

# ==============================
# 📈 ANALYZE PAGE
# ==============================
if page == "📈 Analyze":

    st.title(f"🚀 Portfolio Intelligence Pro — {st.session_state.user}")

    stocks_input = st.text_area("Stocks (comma separated)", "AAPL,MSFT,GOOGL")
    investment = st.number_input("Investment ₹", value=100000)

    if st.button("Analyze Portfolio"):

        stocks = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]

        if len(stocks) == 0:
            st.error("Enter valid stocks")
            st.stop()

        data = yf.download(stocks, start="2020-01-01", progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data = data["Close"]

        data = data.dropna(axis=1, how="all").dropna()
        returns = data.pct_change().dropna()

        if returns.empty:
            st.error("No valid data")
            st.stop()

        # ==============================
        # OPTIMIZATION
        # ==============================
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

        # ==============================
        # METRICS
        # ==============================
        port_return = np.sum(returns.mean() * weights) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        sharpe = port_return / port_vol if port_vol != 0 else 0

        cumulative = (1 + returns.dot(weights)).cumprod()
        drawdown = (cumulative / cumulative.cummax() - 1).min()

        st.subheader("📊 Key Metrics")

        c1, c2, c3, c4 = st.columns(4)

        c1.markdown(f"<div class='metric-card'><h3>Return</h3><h2>{port_return*100:.2f}%</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><h3>Volatility</h3><h2>{port_vol*100:.2f}%</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><h3>Sharpe</h3><h2>{sharpe:.2f}</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><h3>Drawdown</h3><h2>{drawdown*100:.2f}%</h2></div>", unsafe_allow_html=True)

        # ==============================
        # ADVANCED TABLE
        # ==============================
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
        alloc["Current Value ₹"] = alloc["Quantity"] * alloc["Current Price"]

        alloc["P&L ₹"] = alloc["Current Value ₹"] - alloc["Investment ₹"]
        alloc["Return %"] = (alloc["P&L ₹"] / alloc["Investment ₹"]) * 100

        alloc = alloc.sort_values(by="Weight (%)", ascending=False)

        # ==============================
        # TABS UI
        # ==============================
        tab1, tab2, tab3 = st.tabs(["📊 Allocation", "📈 Performance", "📄 Details"])

        with tab1:
            st.bar_chart(alloc.set_index("Stock")["Weight (%)"])

        with tab2:
            st.line_chart(cumulative)

        with tab3:
            st.dataframe(alloc)

        # ==============================
        # DOWNLOAD
        # ==============================
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            alloc.to_excel(writer, sheet_name='Portfolio', index=False)
            cumulative.to_frame(name="Growth").to_excel(writer, sheet_name='Performance')

        buffer.seek(0)

        st.download_button(
            label="📥 Download Report",
            data=buffer,
            file_name="portfolio_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # ==============================
        # SAVE
        # ==============================
        if st.button("💾 Save Portfolio"):
            try:
                supabase.table("portfolios").insert({
                    "username": st.session_state.user,
                    "stocks": stocks_input
                }).execute()

                st.success("Saved successfully!")

            except Exception as e:
                st.error(e)

# ==============================
# 📁 SAVED PORTFOLIOS
# ==============================
if page == "📁 Saved Portfolios":

    st.title("📁 Your Saved Portfolios")

    try:
        response = supabase.table("portfolios") \
            .select("*") \
            .eq("username", st.session_state.user) \
            .execute()

        if response.data:
            for row in response.data:
                st.success(row["stocks"])
        else:
            st.info("No portfolios yet")

    except Exception as e:
        st.error(e)

# ==============================
# ⚙️ SETTINGS
# ==============================
if page == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.write("Future features coming soon...")
