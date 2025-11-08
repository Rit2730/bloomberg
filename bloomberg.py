# elite_market_dashboard.py
# Professional-style Streamlit financial dashboard (no extra installs).
# - Live quotes via Yahoo Finance public JSON endpoint (requests only)
# - News aggregation from RSS (Economic Times, Times of India) and BSE/NSE/AMFI best-effort
# - After-hours filter (India market close: 15:30 IST)
# - Geopolitical / market-impact heuristics
# - Glossy black theme via CSS
# NOTE: For enterprise reliability use paid/licensed APIs and put keys into st.secrets

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import pandas as pd
import html
import re

# ----------------------- Config -----------------------
st.set_page_config(page_title="EliteMarket — Live Finance Dashboard", layout="wide")
IST_OFFSET = timedelta(hours=5, minutes=30)
MARKET_CLOSE_IST = (15, 30)  # 15:30 IST is exchange close for NSE/BSE regular session

# Example feeds (add/remove as needed). Some sources have multiple feed URLs.
RSS_FEEDS = {
    "Economic Times - Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Times of India - Business": "https://timesofindia.indiatimes.com/rssfeeds/1221656.cms",
    "Moneycontrol - Markets": "https://www.moneycontrol.com/rss/markets.xml",
    "BSE News (RSS - example)": "https://www.bseindia.com/xml-data/corpfiling/Equity/Equity.xml",  # BSE has XML for corp filings (sample)
    # AMFI does not provide a neat RSS; we'll attempt to read its announcements page as HTML.
    "AMFI News (site)": "https://www.amfiindia.com/latest-news"  
}

# Add more targeted feeds (company news) if desired
ADDITIONAL_FEEDS = [
    # "https://www.thehindubusinessline.com/markets/whatever/rss",
]

# ----------------------- CSS (glossy black theme) -----------------------
st.markdown(
    """
    <style>
    /* page */
    .stApp { background: radial-gradient(circle at 10% 10%, #101010, #050505); color: #e6eef8; }
    /* container cards */
    .stCard, .css-1d391kg, .css-1v3fvcr { background: rgba(20,20,20,0.6); border: 1px solid rgba(255,255,255,0.04); }
    /* links */
    a { color: #4fb0ff; text-decoration: none; }
    a:hover { color: #9be1ff; }
    /* headers */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2 { color: #ffffff; }
    /* metrics style */
    .stMetric { color: #e6eef8 !important; }
    /* table header */
    .stDataFrame thead th { color: #dbeafe; background: rgba(255,255,255,0.02); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------- Utilities -----------------------
def now_ist():
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz=timezone.utc) + IST_OFFSET

def parse_rss(url, max_items=10):
    """Fetch RSS / XML and return list of dicts (title, link, pubDate, summary, source)."""
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        content = r.content
        root = ET.fromstring(content)
        items = []
        for elem in root.findall(".//item")[:max_items]:
            title = elem.findtext("title") or ""
            link = elem.findtext("link") or ""
            pub = elem.findtext("pubDate") or elem.findtext("published") or ""
            desc = elem.findtext("description") or elem.findtext("summary") or ""
            items.append({
                "title": html.unescape(title.strip()),
                "link": link.strip(),
                "published": pub.strip(),
                "summary": re.sub(r'<[^>]+>', '', desc).strip(),
            })
        return items
    except Exception:
        return []

def fetch_yahoo_quote(symbol):
    """
    Fetch real-time-ish quote from Yahoo Finance public endpoint.
    Returns dict with price, change, percent, time. Works for equities and indices.
    """
    try:
        # Yahoo API accepts comma-separated symbols. Careful with special chars.
        safe = requests.utils.quote(symbol)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={safe}"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        js = r.json()
        q = js.get("quoteResponse", {}).get("result", [])
        if not q:
            return None
        q0 = q[0]
        return {
            "symbol": q0.get("symbol"),
            "shortName": q0.get("shortName") or q0.get("longName"),
            "price": q0.get("regularMarketPrice"),
            "previousClose": q0.get("regularMarketPreviousClose"),
            "change": q0.get("regularMarketChange"),
            "percent": q0.get("regularMarketChangePercent"),
            "time": datetime.fromtimestamp(q0.get("regularMarketTime") or datetime.utcnow().timestamp())
        }
    except Exception:
        return None

def fetch_bse_announcements(limit=10):
    """
    Best-effort attempt to fetch corporate filings/announcements from BSE XML endpoint.
    BSE publishes company-wise XMLs; here we try a bulk feed (may return empty).
    """
    url = "https://www.bseindia.com/xml-data/corpfiling/Equity/Equity.xml"
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        # sample structure parsing may differ; we'll attempt to locate announcement nodes
        items = []
        for ann in root.findall(".//Announcement")[:limit]:
            title = ann.findtext("Subject") or ann.findtext("Head") or "Announcement"
            date = ann.findtext("Dt") or ann.findtext("Date")
            link = ann.findtext("URL") or ""
            items.append({"title": title, "date": date, "link": link})
        return items
    except Exception:
        return []

# Simple heuristics to tag geopolitical / macro / action items
GEO_KEYWORDS = [
    "sanction", "war", "conflict", "geopolit", "tariff", "trade war", "election", "sanctions", "military",
    "rally", "protest", "embargo", "blockade", "cyber attack", "terror"
]
MACRO_KEYWORDS = ["inflation", "cpi", "gdp", "unemployment", "rate cut", "rate hike", "interest rate", "rbi", "fed"]
ACTION_KEYWORDS = ["dividend", "buyback", "board", "merger", "acquisition", "ipo", "rights issue", "debt"]

def tag_article(text):
    txt = (text or "").lower()
    tags = []
    if any(k in txt for k in GEO_KEYWORDS):
        tags.append("Geopolitical")
    if any(k in txt for k in MACRO_KEYWORDS):
        tags.append("Macro")
    if any(k in txt for k in ACTION_KEYWORDS):
        tags.append("Corporate Action")
    return tags or ["General"]

def is_after_hours(pub_dt_str):
    """
    Try to parse pub_dt_str for known formats; treat it as after-hours if published after 15:30 IST.
    If parsing fails, return False (conservative).
    """
    try:
        # try common RFC formats
        pub = None
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                pub = datetime.strptime(pub_dt_str, fmt)
                break
            except Exception:
                continue
        if pub is None:
            # fallback: find digits
            m = re.search(r"(\d{2}:\d{2}:\d{2})", pub_dt_str)
            if not m:
                return False
            # assume today's date
            today = now_ist().date()
            hms = m.group(1)
            pub = datetime.combine(today, datetime.strptime(hms, "%H:%M:%S").time())
        # convert to IST if naive (we'll assume UTC if naive) — approximate
        if pub.tzinfo is None:
            pub_utc = pub.replace(tzinfo=timezone.utc)
            pub_ist = pub_utc.astimezone(timezone.utc) + IST_OFFSET
        else:
            pub_ist = pub.astimezone(timezone.utc) + IST_OFFSET
        return (pub_ist.hour, pub_ist.minute) >= MARKET_CLOSE_IST
    except Exception:
        return False

# ----------------------- UI -----------------------
st.title("EliteMarket — Professional Live Finance Dashboard")
st.markdown("Aggregates live quotes, multi-source financial news, corporate announcements, and geopolitical/macro impact flags. For production-grade reliability, plug premium APIs (see bottom).")

# Sidebar controls
with st.sidebar:
    st.header("Controls")
    symbols_input = st.text_input("Tickers / Indices (comma separated)", value="NSEI, ^BSESN, TCS.NS, RELIANCE.NS, ITC.NS")
    symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
    st.markdown("---")
    st.subheader("News feeds")
    feeds_checked = st.multiselect("Select sources to include", options=list(RSS_FEEDS.keys()), default=list(RSS_FEEDS.keys()))
    st.number_input("Articles per source", min_value=3, max_value=30, value=10, key="articles_per")
    st.checkbox("Show only after-market articles", key="after_hours", value=False)
    st.checkbox("Highlight Geopolitical / Macro / Corporate actions", key="highlight_tags", value=True)
    st.markdown("---")
    st.caption("Note: For full enterprise data (real-time tick-by-tick, official corporate filings), use licensed APIs. See README for how to add keys to Streamlit Secrets.")

# Top row: live quotes
st.subheader("Live Quotes")
quote_cols = st.columns(len(symbols) if symbols else 1)
quotes = []
for i, s in enumerate(symbols):
    q = fetch_yahoo_quote(s)
    quotes.append(q)
    c = quote_cols[i]
    if q:
        pct = q.get("percent")
        sign = "↗️" if pct and pct > 0 else ("↘️" if pct and pct < 0 else "—")
        c.metric(label=f"{q.get('symbol')} — {q.get('shortName') or ''}", value=f"{q.get('price')}", delta=f"{pct:.2f}%" if pct is not None else "n/a")
    else:
        c.write(f"{s} — data n/a")

# Middle: consolidated market data table (DataFrame)
st.subheader("Market Snapshot Table")
snap_rows = []
for q in quotes:
    if q:
        snap_rows.append({
            "Symbol": q.get("symbol"),
            "Name": q.get("shortName"),
            "Price": q.get("price"),
            "Change": q.get("change"),
            "Change %": q.get("percent")
        })
snap_df = pd.DataFrame(snap_rows)
st.dataframe(snap_df, use_container_width=True)

# News aggregation
st.subheader("News & Corporate Announcements")
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### Aggregated News")
    NEWS = []
    # gather feeds selected
    for feed_name in feeds_checked:
        url = RSS_FEEDS.get(feed_name)
        if not url:
            continue
        items = parse_rss(url, max_items=st.session_state.articles_per)
        for it in items:
            it["source"] = feed_name
        NEWS.extend(items)

    # AMFI / BSE attempts
    # BSE corporate XML
    bse_anns = fetch_bse_announcements(limit=8)
    for a in bse_anns:
        NEWS.append({"title": a.get("title"), "link": a.get("link"), "published": a.get("date"), "summary": "", "source": "BSE Announcements"})

    # sort by published (best-effort) — if published missing, push to end
    def pub_key(x):
        p = x.get("published") or ""
        return p
    NEWS = sorted(NEWS, key=pub_key, reverse=True)

    # filter after-hours if requested
    if st.session_state.after_hours:
        NEWS = [n for n in NEWS if is_after_hours(n.get("published", ""))]

    # remove duplicates (same title)
    seen = set()
    NEWS_UNIQ = []
    for item in NEWS:
        t = item.get("title") or ""
        if t in seen:
            continue
        seen.add(t)
        NEWS_UNIQ.append(item)
    NEWS = NEWS_UNIQ

    # display
    if not NEWS:
        st.info("No articles available. Check internet or change sources.")
    else:
        for n in NEWS[:60]:
            title = n.get("title")
            link = n.get("link")
            pub = n.get("published")
            summary = n.get("summary") or ""
            source = n.get("source", "News")
            tags = tag_article(f"{title} {summary}")

            st.markdown(f"#### [{title}]({link})")
            st.caption(f"{source} • {pub}")
            if summary:
                st.write(summary)
            if st.session_state.highlight_tags:
                st.markdown("**Tags:** " + ", ".join(f"`{t}`" for t in tags))
            st.markdown("---")

with col_right:
    st.markdown("### Corporate Announcements (BSE / NSE sample)")
    if bse_anns:
        st.table(pd.DataFrame(bse_anns))
    else:
        st.write("No structured BSE announcements found. To get the full corporate announcements feed, use BSE/NSE official APIs (paid or licensed).")
    st.markdown("### Quick Actions / What to watch")
    st.write("""
    - **Earnings / Results**: watch quarterly results and management commentary.  
    - **RBI / Fed announcements**: high impact for rates & financial stocks.  
    - **Macro prints**: CPI, GDP, Unemployment drive bond yields & markets.  
    - **Geopolitical shocks**: trade sanctions, wars, or large-scale protests cause volatility.  
    - **Corporate actions**: buybacks/dividends/mergers change valuation perceptions.
    """)
    st.markdown("### Suggested Next Steps (for production)")
    st.write("""
    1. Add licensed streaming price API (IEX / Finnhub / Exchange-provided).  
    2. Subscribe to corporate filings feed (BSE/NSE paid data or vendor).  
    3. Normalise news text and run named-entity recognition (NER) to extract companies, countries, persons.  
    4. Add user watchlists, alerts and historical charting (candlestick + indicators).  
    """)

# Bottom: geopolitical + impact summary
st.subheader("Macro / Geopolitical Impact Summary (auto flagged)")
# aggregate tags counts
tag_counts = {}
for n in NEWS:
    for t in tag_article((n.get("title") or "") + " " + (n.get("summary") or "")):
        tag_counts[t] = tag_counts.get(t, 0) + 1
if not tag_counts:
    st.write("No significant tags detected.")
else:
    st.table(pd.DataFrame(list(tag_counts.items()), columns=["Tag", "Count"]))

# Footer: How to plug paid APIs (instructions)
st.markdown("---")
st.markdown("## Production Integration (Recommended)")
st.markdown("""
**To convert this proof-of-concept into a complete, reliable application, integrate these:**
- **Real-time price/quotes**: IEX Cloud, Finnhub, Refinitiv, Alpha Vantage (note rate limits), or exchange direct feeds (NSE/BSE) for India.  
- **News & filings**: licensed news feeds for full-text (Economic Times enterprise, Reuters, Bloomberg), and official corporate filings endpoints for BSE/NSE.  
- **Storage & search**: persisted article DB (Elasticsearch), to enable search, relevance ranking, and historical queries.  
- **NLP**: use spaCy or transformers for NER, sentiment and event extraction (requires adding Python dependencies).  
- **Deployment**: use Docker, CI, and run on a server with secrets (never hard-code API keys).
""")

st.success("Demo ready — add API keys into Streamlit Secrets and replace the simple fetch functions with vendor-specific endpoints for production-grade coverage.")
