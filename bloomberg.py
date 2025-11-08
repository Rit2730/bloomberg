import os
import time
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import requests
import feedparser

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except Exception:
    HAS_TEXTBLOB = False

st.set_page_config(page_title="MiniBloom - Financial Dashboard", layout="wide")

@st.cache_data(ttl=60)
def fetch_price_history(ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval)
    if df.empty:
        return df
    df = df.reset_index()
    return df

@st.cache_data(ttl=60)
def fetch_quote_info(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    info = tk.info
    return info

@st.cache_data(ttl=300)
def fetch_news(query: str, pages: int = 1) -> list:
    api_key = os.getenv("NEWSAPI_KEY")
    articles = []

    if api_key:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey": api_key,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            for a in data.get("articles", []):
                articles.append({
                    "title": a.get("title"),
                    "link": a.get("url"),
                    "published": a.get("publishedAt"),
                    "source": a.get("source", {}).get("name"),
                    "summary": a.get("description") or "",
                })
        except Exception:
            api_key = None

    if not api_key:
        q = query.replace(" ", "+")
        rss_url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(rss_url)
            for e in feed.entries[:20 * pages]:
                published = getattr(e, 'published', '')
                articles.append({
                    "title": e.title,
                    "link": e.link,
                    "published": published,
                    "source": e.get('source', {}).get('title', '') if e.get('source') else '',
                    "summary": e.get('summary', ''),
                })
        except Exception:
            pass

    return articles

def simple_sentiment(text: str) -> float:
    if not HAS_TEXTBLOB or not text:
        return 0.0
    analysis = TextBlob(text)
    return round(analysis.sentiment.polarity, 3)

st.title("MiniBloom — Financial & Market Dashboard")
st.markdown("A prototype Streamlit app for market data, charts, watchlists and news — suitable for a college project.")

with st.sidebar:
    st.header("Controls")
    default_tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM", "^NSEI", "^GSPC"]
    tickers_input = st.text_area("Tickers / Indices (comma separated)", value=", ".join(default_tickers), help="Examples: AAPL, MSFT, TSLA, ^GSPC, ^NSEI")
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

    period = st.selectbox("History Period", options=["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("Interval", options=["1d", "1wk", "1mo", "60m", "30m"], index=0)

    st.markdown("---")
    st.subheader("News")
    news_query = st.text_input("Search news for", value="financial markets")
    use_sentiment = st.checkbox("Enable simple sentiment analysis (TextBlob)", value=False)
    refresh = st.button("Refresh Now")

cols = st.columns([2, 1])

with cols[0]:
    st.subheader("Watchlist & Charts")
    selected = st.selectbox("Select ticker for detailed view", options=tickers)

    if selected:
        with st.spinner(f"Fetching data for {selected}..."):
            df = fetch_price_history(selected, period=period, interval=interval)
            info = fetch_quote_info(selected)

        if df.empty:
            st.warning("No historical data found for this ticker — check the symbol (try ^GSPC for S&P500, ^NSEI for Nifty).")
        else:
            fig = px.line(df, x=df.columns[0], y="Close", title=f"{selected} — Close Price")
            fig.update_layout(height=420, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change = (latest['Close'] - prev['Close']) / prev['Close'] * 100 if prev['Close'] != 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric(label="Last Close", value=f"{latest['Close']:.2f}")
            c2.metric(label="Change (vs prev)", value=f"{change:.2f}%")
            c3.metric(label="Volume", value=int(latest.get('Volume', 0)))

            st.markdown("**Key Info**")
            try:
                st.write({
                    "shortName": info.get('shortName'),
                    "market": info.get('exchange'),
                    "sector": info.get('sector'),
                    "marketCap": info.get('marketCap'),
                })
            except Exception:
                pass

            st.markdown("**Historical data (last rows)**")
            st.dataframe(df.tail(10))

with cols[1]:
    st.subheader("Market Snapshot")
