import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import io
import requests

# ================= CONFIG =================
st.set_page_config(page_title="Portfolio Intelligence Pro", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)
# ================= PREMIUM UI STYLE =================
st.markdown("""
<style>

/* Background */
.main {
    background-color: #0b0f1a;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
}

cols[i].markdown(f"""
<div class="card">
<h3>{row['Stock']}</h3>
<h1>₹{row['Price']:.2f}</h1>
<p style="color:{color};font-size:18px;">
{row['Change %']:.2f}%
</p>
</div>
""", unsafe_allow_html=True)

/* Headers */
h1, h2, h3 {
    color: #e5e7eb;
}

/* Metrics */
.metric {
    font-size: 20px;
    font-weight: bold;
}

/* Buttons */
.stButton>button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    padding: 10px;
}

/* Input boxes */
.stTextInput>div>div>input {
    background-color: #111827;
    color: white;
}

/* Dataframe */
.css-1d391kg {
    background-color: #111827;
}

</style>
""", unsafe_allow_html=True)
# ================= PERFORMANCE SETTINGS =================
st_autorefresh(interval=10000, key="live_refresh")  # slower refresh

# ================= STYLE =================
st.markdown("""
<style>
body {background-color:#0b0f1a;color:#e6e6e6;}
.card {background:#111827;padding:15px;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ================= CACHE =================
@st.cache_data(ttl=5)
def get_live_price(stock, api_key):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={stock}&token={api_key}"
        r = requests.get(url).json()

        if r and "c" in r and r["c"] != 0:
            price = r["c"]
            prev = r["pc"]
            change = ((price - prev) / prev) * 100
            return price, change
    except:
        return None, None

@st.cache_data(ttl=60)
def get_stock_data(stock):
    try:
        data = yf.download(stock, period="6mo", progress=False)
        return data["Close"]
    except:
        return None

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

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
    st.title("🚀 Portfolio Intelligence Pro")
    st.stop()

user = st.session_state.user

# ================= NAV =================
page = st.sidebar.radio("Navigate", ["Dashboard", "Terminal", "Analyze", "Portfolios"])

# ================= TERMINAL =================
if page == "Terminal":

    st.title("💻 Live Trading Terminal")

    watchlist = st.text_input("Watchlist", "AAPL,MSFT,TSLA")
    stocks = [s.strip().upper() for s in watchlist.split(",")]

    api_key = st.secrets["FINNHUB_API_KEY"]

    with st.spinner("Fetching live data..."):
        data_rows = []

        for stock in stocks:
            price, change = get_live_price(stock, api_key)

            if price is not None:
                data_rows.append({
                    "Stock": stock,
                    "Price": price,
                    "Change %": change
                })

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

# ================= ANALYZE =================
elif page == "Analyze":

    st.title("📈 Portfolio Intelligence")

    stocks_input = st.text_input("Stocks + Quantity", "AAPL:10,MSFT:5,TSLA:2")

    if st.button("Analyze"):
        st.session_state.analysis_done = True

        items = [s.strip() for s in stocks_input.split(",")]

        stocks = []
        quantity = {}

        for item in items:
            try:
                stock, qty = item.split(":")
                stock = stock.upper()
                qty = float(qty)

                stocks.append(stock)
                quantity[stock] = qty
            except:
                continue

        price_data = {}
        valid = []

        for stock in stocks:
            data = get_stock_data(stock)

            if data is not None:
                price_data[stock] = data
                valid.append(stock)

        if not price_data:
            st.error("No valid stocks")
            st.stop()

        data = pd.concat(price_data.values(), axis=1)
        data.columns = valid
        data = data.dropna()

        latest = data.iloc[-1]
        buy = data.iloc[0]

        df = pd.DataFrame({"Stock": valid})

        df["Qty"] = df["Stock"].map(quantity)
        df["Buy"] = df["Stock"].map(buy)
        df["LTP"] = df["Stock"].map(latest)

        df["Invested"] = df["Qty"] * df["Buy"]
        df["Value"] = df["Qty"] * df["LTP"]
        df["P&L"] = df["Value"] - df["Invested"]

        st.session_state.result_df = df

        # ===== SAVE HISTORY =====
        try:
            total_value = df["Value"].sum()

            supabase.table("portfolio_history").insert({
                "username": user,
                "portfolio_name": "default",
                "date": pd.Timestamp.today().date().isoformat(),
                "value": float(total_value)
            }).execute()
        except:
            pass

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

        # ===== HISTORY =====
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

        st.download_button("📥 Download", buffer, "portfolio.xlsx")

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

    try:
        res = supabase.table("portfolios").select("*").eq("username", user).execute()

        for r in res.data:
            st.markdown(f"**{r['portfolio_name']}** → {r['stocks']}")
    except:
        st.warning("No portfolios found")
# ================= DASHBOARD =================
if page == "Dashboard":

    st.title("📊 Portfolio Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Portfolio Value", "₹1,25,000", "+2.5%")
    col2.metric("Today's P&L", "₹2,300", "+1.2%")
    col3.metric("Total Invested", "₹1,00,000")
    col4.metric("Active Stocks", "8")

    st.divider()

    st.subheader("📈 Market Overview")

    sample_data = pd.DataFrame({
        "Index": ["NIFTY 50", "SENSEX", "NASDAQ"],
        "Value": [22400, 73000, 18000],
        "Change %": [0.5, -0.2, 1.1]
    })

    st.dataframe(sample_data, use_container_width=True)

    st.divider()

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
        st.warning("No history data yet")
