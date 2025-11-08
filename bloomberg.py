import streamlit as st
import sys
import subprocess

# ✅ Auto-install yfinance if missing
try:
    import yfinance as yf
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

# ✅ Auto-install other core dependencies if missing
for pkg in ["plotly", "pandas", "requests", "feedparser"]:
    try:
        __import__(pkg)
    except ModuleNotFoundError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import pandas as pd
import plotly.express as px
import requests
import feedparser
from datetime import datetime, timedelta

st.set_page_config(page_title="Bloomberg Clone", layout="wide")

# Title and intro
st.title("💹 Mini Bloomberg Clone")
st.markdown("A live financial dashboard with market data, charts, and news updates — built using Streamlit!")

# Sidebar
st.sidebar.header("Settings")
st.sidebar.markdown("Use this menu to customize your view.")

# --- SECTION 1: Market Data ---
st.subheader("📈 Market Data")

tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "NIFTY.NS", "BANKNIFTY.NS"]
selected_ticker = st.selectbox("Select Stock / Index:", tickers)

period = st.selectbox("Select Period:", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"])
interval = "1d" if period not in ["1d", "5d"] else "30m"

try:
    data = yf.download(selected_ticker, period=period, interval=interval)
    if not data.empty:
        data.reset_index(inplace=True)
        st.write(f"Showing {selected_ticker} data for {period}")
        fig = px.line(data, x="Date", y="Close", title=f"{selected_ticker} Closing Prices", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available for this selection.")
except Exception as e:
    st.error(f"Error fetching data: {e}")

# --- SECTION 2: Market Summary ---
st.subheader("📊 Market Snapshot")
snapshot = {
    "Index": ["NIFTY 50", "SENSEX", "NASDAQ", "DOW JONES", "S&P 500"],
    "Change %": [0.42, 0.38, -0.15, -0.25, 0.10],
    "Status": ["Up", "Up", "Down", "Down", "Up"]
}
snapshot_df = pd.DataFrame(snapshot)
st.dataframe(snapshot_df, use_container_width=True)

# --- SECTION 3: Financial & Economic News ---
st.subheader("📰 Financial & Economic News")

NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", None)
query = st.text_input("Search Topic:", "stock market")

def fetch_news(query):
    if NEWSAPI_KEY:
        url = f"https://newsapi.org/v2/everything?q={query}&language=en&apiKey={NEWSAPI_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("articles", [])
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={query}")
    return [{"title": e.title, "link": e.link, "publishedAt": e.published} for e in feed.entries[:10]]

articles = fetch_news(query)
if articles:
    for a in articles[:5]:
        st.markdown(f"### [{a.get('title')}]({a.get('link')})")
        if "publishedAt" in a:
            st.caption(a.get("publishedAt"))
else:
    st.warning("No news found. Try a different keyword.")

# --- SECTION 4: Footer ---
st.divider()
st.markdown(
    """
    **Quick Economic / Market Links**
    - [Yahoo Finance](https://finance.yahoo.com)
    - [Moneycontrol](https://www.moneycontrol.com)
    - [Investing.com](https://in.investing.com)
    - [TradingView](https://www.tradingview.com)
    - [Economic Times Markets](https://economictimes.indiatimes.com/markets)
    """
)
st.info("App created for educational purpose — Mini Bloomberg Clone (© 2025).")
