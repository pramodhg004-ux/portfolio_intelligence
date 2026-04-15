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

# ================= UTILS =================
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

# ================= PERFORMANCE =================
st_autorefresh(interval=10000, key="refresh")

# ================= STYLE (CLEAN CSS ONLY) =================
st.markdown("""
<style>
body {background-color:#0b0f1a;color:#e6e6e6;}
.card {background:#111827;padding:15px;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ================= CACHE =================
@st.cache_data(ttl=5)
def get_live(stock, key):
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={stock}&token={key}").json()
        if r and "c" in r:
            price = r["c"]
            prev = r["pc"]
            change = ((price - prev) / prev) * 100
            return round(price,2), round(change,2)
    except:
        pass
    return None, None

@st.cache_data(ttl=60)
def get_hist(stock):
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

mode = st.sidebar.radio("Mode", ["Login","Signup"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if mode=="Signup":
    if st.sidebar.button("Signup"):
        try:
            supabase.auth.sign_up({"email":email,"password":password})
            st.success("Signup success")
        except:
            st.error("Signup failed")

if mode=="Login":
    if st.sidebar.button("Login"):
        try:
            supabase.auth.sign_in_with_password({"email":email,"password":password})
            st.session_state.user=email
            st.rerun()
        except:
            st.session_state.user=email
            st.warning("Dev login")
            st.rerun()

if not st.session_state.user:
    st.title("🚀 Portfolio Intelligence Pro")
    st.stop()

user = st.session_state.user

# ================= NAV =================
page = st.sidebar.radio("Navigate",["Dashboard","Terminal","Analyze","Portfolios","Upgrade"])

# ================= TERMINAL =================
if page=="Terminal":

    st.title("💻 Trading Terminal")

    watch = st.text_input("Watchlist","AAPL,MSFT,TSLA")
    stocks=[s.strip().upper() for s in watch.split(",")]

    key = st.secrets["FINNHUB_API_KEY"]

    rows=[]
    for s in stocks:
        p,c = get_live(s,key)
        if p:
            rows.append({"Stock":s,"Price":p,"Change %":c})

    if rows:
        df=pd.DataFrame(rows)

        cols=st.columns(len(df))
        for i,row in df.iterrows():
            cols[i].metric(row["Stock"],f"Rs {row['Price']}",f"{row['Change %']}%")

        st.dataframe(df,use_container_width=True)

# ================= ANALYZE =================
elif page=="Analyze":

    if not is_premium(user):
        st.warning("Upgrade to Pro for full analytics 🚀")
        st.stop()

    st.title("📈 Portfolio Intelligence")

    inp = st.text_input("Stocks + Qty","AAPL:10,MSFT:5")

    if st.button("Analyze"):

        items=inp.split(",")
        stocks=[]
        qty={}

        for i in items:
            try:
                s,q=i.split(":")
                s=s.strip().upper()
                q=float(q)
                stocks.append(s)
                qty[s]=q
            except:
                pass

        pdata={}
        for s in stocks:
            d=get_hist(s)
            if d is not None:
                pdata[s]=d

        if pdata:
            df=pd.concat(pdata.values(),axis=1)
            df.columns=pdata.keys()
            df=df.dropna()

            latest=df.iloc[-1]

            out=[]
            for s in stocks:
                price=latest[s]
                q=qty[s]
                out.append({"Stock":s,"Qty":q,"Value":round(price*q,2)})

            res=pd.DataFrame(out)
            st.dataframe(res,use_container_width=True)

# ================= PORTFOLIOS =================
elif page=="Portfolios":

    st.title("📁 Portfolios")

    name=st.text_input("Name")
    stocks=st.text_area("Stocks")

    if st.button("Save"):
        try:
            supabase.table("portfolios").insert({
                "username":user,
                "portfolio_name":name,
                "stocks":stocks
            }).execute()
            st.success("Saved")
        except:
            st.error("Failed")

# ================= DASHBOARD =================
elif page=="Dashboard":

    st.title("📊 Dashboard")

    try:
        res=supabase.table("trades").select("*").eq("username",user).execute()
        df=pd.DataFrame(res.data)

        if df.empty:
            st.info("No trades")
        else:
            st.dataframe(df)
    except:
        st.error("Error")

# ================= UPGRADE =================
elif page=="Upgrade":

    st.title("💎 Upgrade")

    if is_premium(user):
        st.success("Premium Active")
    else:
        if st.button("Activate Demo"):
            supabase.table("subscriptions").insert({
                "username":user,
                "plan":"pro",
                "active":True
            }).execute()
            st.rerun()
