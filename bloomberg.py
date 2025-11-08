import streamlit as st
import requests
import datetime

# ------------------ BASIC APP SETUP ------------------
st.set_page_config(page_title="Bloomberg Clone", layout="wide")
st.title("💹 Mini Bloomberg Clone")
st.markdown("A simplified version of Bloomberg — live news and market summaries in one place!")

# ------------------ SIDEBAR ------------------
st.sidebar.header("Navigation")
section = st.sidebar.radio("Go to:", ["🏦 Market Overview", "📰 Financial News", "📅 Economic Calendar"])

# ------------------ MARKET OVERVIEW ------------------
if section == "🏦 Market Overview":
    st.subheader("📈 Simulated Market Snapshot")

    market_data = [
        {"Index": "NIFTY 50", "Value": 22850.25, "Change%": +0.42},
        {"Index": "SENSEX", "Value": 75580.47, "Change%": +0.38},
        {"Index": "NASDAQ", "Value": 17780.13, "Change%": -0.15},
        {"Index": "DOW JONES", "Value": 39140.25, "Change%": -0.25},
        {"Index": "S&P 500", "Value": 5120.52, "Change%": +0.10},
    ]

    st.table(market_data)

    st.markdown("#### 🔍 Market Highlights")
    st.write("""
    - Indian markets remain **positive** on the back of strong quarterly earnings.  
    - Global indices show **mixed trends** due to US inflation concerns.  
    - Oil prices stabilize as OPEC maintains supply targets.  
    """)

# ------------------ FINANCIAL NEWS ------------------
elif section == "📰 Financial News":
    st.subheader("🗞️ Latest Financial & Economic News")

    query = st.text_input("Search for a topic:", "finance")
    st.caption("Example: 'stock market', 'RBI policy', 'crude oil', 'inflation'")

    # Use Google News RSS (works without API key)
    try:
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(rss_url, timeout=5)

        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            items = root.findall(".//item")
            if items:
                for item in items[:8]:
                    title = item.find("title").text
                    link = item.find("link").text
                    pubDate = item.find("pubDate").text
                    st.markdown(f"### [{title}]({link})")
                    st.caption(pubDate)
            else:
                st.warning("No articles found. Try another topic.")
        else:
            st.error("Unable to fetch news right now.")
    except Exception:
        st.warning("Unable to connect to the news server. Please check your internet connection.")

# ------------------ ECONOMIC CALENDAR ------------------
elif section == "📅 Economic Calendar":
    st.subheader("📆 Upcoming Global Economic Events")

    today = datetime.date.today()
    events = [
        {"Date": today + datetime.timedelta(days=1), "Event": "US CPI Inflation Report", "Impact": "High"},
        {"Date": today + datetime.timedelta(days=2), "Event": "India GDP Growth Data", "Impact": "High"},
        {"Date": today + datetime.timedelta(days=3), "Event": "Eurozone Interest Rate Decision", "Impact": "Medium"},
        {"Date": today + datetime.timedelta(days=4), "Event": "US Initial Jobless Claims", "Impact": "Medium"},
        {"Date": today + datetime.timedelta(days=5), "Event": "China Manufacturing PMI", "Impact": "High"},
    ]

    st.table(events)
    st.info("Calendar is auto-generated for demonstration purposes.")

# ------------------ FOOTER ------------------
st.divider()
st.markdown("""
**Quick Links**
- [Moneycontrol](https://www.moneycontrol.com)
- [Investing.com](https://in.investing.com)
- [Economic Times Markets](https://economictimes.indiatimes.com/markets)
""")

st.success("✅ App running successfully — no external installs required!")
