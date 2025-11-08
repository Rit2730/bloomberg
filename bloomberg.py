import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import date, timedelta

# ------------------ Page & Theme Setup ------------------
st.set_page_config(page_title="EliteMarket Dashboard", layout="wide")

# Apply custom CSS for glossy black theme
st.markdown(
    """
    <style>
    body {
        background-color: #0f0f0f;
        color: #e0e0e0;
    }
    .css-1d391kg {background-color: #0f0f0f;}
    .css-1v3fvcr {background-color: #1a1a1a;}
    a {
        color: #1e90ff;
    }
    .stButton>button {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #444;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("EliteMarket Dashboard")
st.markdown("A professional financial dashboard — black-theme, curated news from top Indian outlets, market snapshots, and more.")

# ------------------ Sidebar Controls ------------------
with st.sidebar:
    st.header("Navigation")
    section = st.radio("Go to:", ["Market Snapshot", "News Feed", "Corporate Announcements"])
    st.markdown("---")
    st.subheader("News Settings")
    news_query = st.text_input("Search topic:", "Indian stock market")
    num_articles = st.slider("Number of articles", 5, 20, 10)

# ------------------ News Feed Section ------------------
if section == "News Feed":
    st.subheader("📰 Latest News")
    # Example RSS feed from Economic Times markets section:
    rss_url = f"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"  # example Markets feed
    try:
        resp = requests.get(rss_url, timeout=5)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        count = 0
        for item in items:
            if count >= num_articles:
                break
            title = item.find("title").text
            link = item.find("link").text
            pubDate = item.find("pubDate").text
            description = item.find("description").text if item.find("description") is not None else ""
            if news_query.lower() in title.lower() or news_query.lower() in description.lower():
                st.markdown(f"### [{title}]({link})")
                st.caption(pubDate)
                st.write(description)
                st.markdown("— — —")
                count += 1
        if count == 0:
            st.info("No matching articles found for your query. Try changing the topic.")
    except Exception as e:
        st.error("Unable to fetch RSS feed. Please check connection or feed URL.")

# ------------------ Market Snapshot Section ------------------
elif section == "Market Snapshot":
    st.subheader("📊 Market Snapshot (Simulated / Sample Data)")
    # Because free live Indian market APIs are limited without paid subscription,
    # we'll show sample data. You can replace this with your own data source later.
    data = [
        {"Index": "Nifty 50", "Value": 23150.45, "Change %": "+0.55%"},
        {"Index": "Sensex", "Value": 76430.12, "Change %": "+0.48%"},
        {"Index": "Mid-Cap Index", "Value": 15220.77, "Change %": "-0.12%"},
    ]
    st.table(data)
    st.markdown("Use a suitable API to replace with live/real-time index data.")

# ------------------ Corporate Announcements Section ------------------
elif section == "Corporate Announcements":
    st.subheader("🏛️ Latest Corporate Announcements from BSE / NSE Listings")
    # Example: BSE listing announcements page (not structured RSS)
    st.markdown("Currently showing sample/company-specific announcements. Need a formal API for entire list.")
    announcements = [
        {"Date": (date.today() - timedelta(days=1)).isoformat(), "Company": "XYZ Ltd", "Update": "Board meeting scheduled for 12/12/2025"},
        {"Date": (date.today() - timedelta(days=2)).isoformat(), "Company": "ABC Corp", "Update": "Dividend announced of ₹2/share"},
    ]
    st.table(announcements)

# ------------------ Footer ------------------
st.markdown("---")
st.markdown(
    """
    **Quick Links**  
    • [Economic Times Markets](https://economictimes.indiatimes.com/markets)  
    • [BSE Corporate Announcements](https://www.bseindia.com/corporates/ann.html)  
    • [National Stock Exchange India](https://www.nseindia.com)  
    """
)
