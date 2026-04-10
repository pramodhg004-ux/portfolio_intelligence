import streamlit as st
import pandas as pd

st.set_page_config(page_title="Portfolio Intelligence", layout="wide")

st.title("🚀 Portfolio Intelligence Dashboard")

base_path = r"C:\Users\Pramodh G\OneDrive\Desktop"

output = pd.read_excel(base_path + r"\portfolio_output.xlsx")
weights = pd.read_excel(base_path + r"\portfolio_weights.xlsx")
growth = pd.read_excel(base_path + r"\portfolio_growth.xlsx")
signals = pd.read_excel(base_path + r"\signals.xlsx")

# ==============================
# METRICS (TOP CARDS)
# ==============================
st.subheader("📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Return", f"{output.iloc[0,1]*100:.2f}%")
col2.metric("Volatility", f"{output.iloc[1,1]*100:.2f}%")
col3.metric("Sharpe", f"{output.iloc[2,1]:.2f}")
col4.metric("Max Drawdown", f"{output.iloc[3,1]*100:.2f}%")

# ==============================
# ALLOCATION
# ==============================
st.subheader("📊 Portfolio Allocation")
st.bar_chart(weights.set_index("Stock"))

# ==============================
# GROWTH
# ==============================
st.subheader("📈 Portfolio Growth")
st.line_chart(growth.set_index("Date"))

# ==============================
# SIGNALS
# ==============================
st.subheader("💡 Buy / Sell Signals")
st.dataframe(signals)