import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import io
import requests

def is_premium(user):
    try:
        res = supabase.table("subscriptions") \
            .select("*") \
            .eq("username", user) \
            .eq("active", True) \
            .execute()

        return len(res.data) > 0
    except:
        return False

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
<h1>Rs {row['Price']}</h1>
<p style="color:{color};font-size:18px;">
{row['Change %']}%
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
page = st.sidebar.radio("Navigate", ["Dashboard", "Terminal", "Analyze", "Portfolios", "Upgrade"])

# ================= TERMINAL =================
# ================= TERMINAL (ZERODHA STYLE) =================
# ================= TERMINAL (PRO TRADING) =================
# ================= TERMINAL (TRADING + SAVE) =================
import plotly.graph_objects as go

if page == "Terminal":

    st.title("💻 Trading Terminal Pro")

    watchlist_input = st.text_area("Watchlist", "AAPL,MSFT,TSLA")
    stocks = [s.strip().upper() for s in watchlist_input.split(",")]

    api_key = st.secrets["FINNHUB_API_KEY"]

    col_left, col_right = st.columns([1, 3])

    with col_left:
        selected_stock = st.radio("Select Stock", stocks, label_visibility="collapsed")

    with col_right:

        st.subheader(f"{selected_stock}")

        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={selected_stock}&token={api_key}"
            r = requests.get(url).json()

            price = r.get("c", 0)
            prev = r.get("pc", 1)
            change = ((price - prev) / prev) * 100

        except:
            price = 0
            change = 0

        color = "green" if change > 0 else "red"

        st.markdown(f"""
        <div style="background:#111827;padding:20px;border-radius:10px;text-align:center;">
            <h1>Rs {price:.2f}</h1>
            <h3 style="color:{color};">{change:.2f}%</h3>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ===== CHART =====
        try:
            data = yf.download(selected_stock, period="1mo", progress=False)

            fig = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close']
            )])

            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

        except:
            st.warning("Chart not available")

        st.divider()

        # ===== TRADE =====
      if is_premium(user):
    st.subheader("💰 Trade")

        qty = st.number_input("Quantity", min_value=1, value=1)

        col1, col2 = st.columns(2)

        if col1.button("Buy"):
            try:
                supabase.table("trades").insert({
                    "username": user,
                    "stock": selected_stock,
                    "qty": qty,
                    "price": price,
                    "side": "BUY"
                }).execute()

                st.success("Buy order executed")
            except:
                st.error("Trade failed")

        if col2.button("Sell"):
            try:
                supabase.table("trades").insert({
                    "username": user,
                    "stock": selected_stock,
                    "qty": qty,
                    "price": price,
                    "side": "SELL"
                }).execute()

                st.warning("Sell order executed")
            except:
                st.error("Trade failed")
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
        
        if not is_premium(user):
    st.warning("Upgrade to Pro for full analytics 🚀")
    st.stop()

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
# ================= DASHBOARD (REAL DATA) =================
if page == "Dashboard":

    st.title("📊 Portfolio Dashboard")

    try:
        res = supabase.table("trades") \
            .select("*") \
            .eq("username", user) \
            .execute()

        trades = pd.DataFrame(res.data)

        if trades.empty:
            st.info("No trades yet")
            st.stop()

        trades["signed_qty"] = trades.apply(
            lambda x: x["qty"] if x["side"] == "BUY" else -x["qty"], axis=1
        )

        holdings = trades.groupby("stock")["signed_qty"].sum().reset_index()

        holdings = holdings[holdings["signed_qty"] > 0]

        total_value = 0

        rows = []

        for _, row in holdings.iterrows():
            stock = row["stock"]
            qty = row["signed_qty"]

            url = f"https://finnhub.io/api/v1/quote?symbol={stock}&token={st.secrets['FINNHUB_API_KEY']}"
            r = requests.get(url).json()

            price = r.get("c", 0)

            value = qty * price
            total_value += value

            rows.append({
                "Stock": stock,
                "Qty": qty,
                "Price": price,
                "Value": value
            })

        df = pd.DataFrame(rows)

        st.metric("Portfolio Value", f"Rs {total_value:,.0f}")

        st.dataframe(df, use_container_width=True)

    except:
        st.error("Error loading portfolio")
        # ================= UPGRADE =================
if page == "Upgrade":

    st.title("💎 Upgrade to Pro")

    st.markdown("""
    ### 🚀 Pro Features:
    - Real-time data ⚡
    - Unlimited portfolios 📊
    - Advanced analytics 📈
    - Trading simulation 💰
    """)

    if is_premium(user):
        st.success("You are a Premium User ✅")
    else:
        if st.button("Activate Premium (Demo)"):
            try:
                supabase.table("subscriptions").insert({
                    "username": user,
                    "plan": "pro",
                    "active": True
                }).execute()

                st.success("Premium Activated 🚀")
                st.rerun()
            except:
                st.error("Failed")
