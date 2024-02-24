import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, List

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import redis
import streamlit as st
import streamlit.components.v1 as components
from text_analysis import get_top_tfidf_words, preprocess_text

# HTML widgets
GOOGLE_TRENDS_CHARTS_URANIUM = "html_widgets/google_trends_charts_uranium.html"
GOOGLE_TRENDS_CHARTS_NUCLEAR = "html_widgets/google_trends_charts_nuclear.html"
TRADINGVIEW_STOCK_CHARTS = "html_widgets/tradingview_stock_charts.html"


@dataclass
class RedisConfig:
    host = os.getenv("REDIS_HOST")
    port = int(os.getenv("REDIS_PORT"))
    db = int(os.getenv("REDIS_DB"))


@contextmanager
def get_redis_connection(redis_config: RedisConfig) -> Iterator[redis.Redis]:
    conn = redis.Redis(
        host=redis_config.host, port=redis_config.port, db=redis_config.db
    )
    try:
        yield conn
    finally:
        pass


def fetch_tweets_dataframe() -> pd.DataFrame:
    redis_config = RedisConfig()
    with get_redis_connection(redis_config) as conn:
        tweets = conn.lrange("tweets", 0, -1)
    tweets_dicts = [json.loads(tweet.decode("utf-8")) for tweet in tweets]
    tweets_df = pd.DataFrame(tweets_dicts)
    tweets_df = tweets_df.sort_values(by="created_at", ascending=False)
    tweets_df = tweets_df[["created_at", "user", "sentiment", "text"]]
    return tweets_df


def fetch_sentiment_time_series_dataframe() -> pd.DataFrame:
    redis_config = RedisConfig()
    with get_redis_connection(redis_config) as conn:
        positive_series = conn.lrange("positive_series", 0, -1)
        negative_series = conn.lrange("negative_series", 0, -1)

    timestamps = []
    positive_counts = []
    negative_counts = []
    for pos, neg in zip(positive_series, negative_series):
        pos_data = pos.decode("utf-8").split(",")
        neg_data = neg.decode("utf-8").split(",")
        timestamps.append(pd.to_datetime(pos_data[0]))
        positive_counts.append(int(pos_data[1]))
        negative_counts.append(int(neg_data[1]))

    data = {
        "Timestamp": timestamps,
        "Positive": positive_counts,
        "Negative": negative_counts,
    }
    df = pd.DataFrame(data)
    df.set_index("Timestamp", inplace=True)
    # Redis data is on a 10 second interval, let's resample to 10 minute interval
    df_resampled = df.resample("10min").sum()
    df_resampled["Formatted_Timestamp"] = df_resampled.index.strftime("%H:%M")
    df_resampled["Ratio"] = df_resampled["Positive"] / (
        df_resampled["Positive"] + df_resampled["Negative"]
    )
    df_resampled.reset_index(inplace=True)
    return df_resampled


def plot_time_series_chart(
    df: pd.DataFrame, window: int = 3, max_bars: int = 20
) -> plt:
    # Only use the last max_bars number of rows from the dataframe. This keeps the
    # number of bars on the chart limited for better readability
    df = df.tail(max_bars)
    plt.close("all")
    plt.figure(figsize=(10, 5))
    plt.bar(
        df["Formatted_Timestamp"],
        df["Ratio"],
        label="Ratio",
        color="silver",
    )
    moving_average = df["Ratio"].rolling(window=window).mean()
    plt.plot(
        df["Formatted_Timestamp"],
        moving_average,
        label=f"Moving Average (Window={window})",
        color="darkred",
    )
    plt.xlabel("Time")
    plt.ylabel("Ratio")
    plt.xticks(rotation=45)
    plt.ylim(0, 1)
    formatter = ticker.PercentFormatter(xmax=1, decimals=0)
    plt.gca().yaxis.set_major_formatter(formatter)
    plt.legend()
    plt.tight_layout()
    return plt


def fetch_top_k_words(tweets: pd.DataFrame, k: int) -> List[str]:
    preprocessed_tweets = [preprocess_text(tweet) for tweet in tweets["text"].tolist()]
    top_k_words = get_top_tfidf_words(preprocessed_tweets, k)
    return top_k_words


def read_html_file(path: str) -> str:
    with open(path, "r") as file:
        html_content = file.read()
    return html_content


# fetch data needed for streamlit
tweets = fetch_tweets_dataframe()
top_k_words = fetch_top_k_words(tweets, 5)
sentiment_time_series = fetch_sentiment_time_series_dataframe()
sentiment_time_series_chart = plot_time_series_chart(sentiment_time_series)

# ----------- Streamlit code starts here -----------

st.set_page_config(page_title="Uranium Dashboard", page_icon="📈", layout="wide")
st.title("Real-time Uranium Dashboard")
st.info(
    "Analyze tweets, top tweet keywords, tweet sentiment, Google Trends, and stock prices for uranium in real-time."
)

tweets_container = st.container()
with tweets_container:
    st.subheader("Tweets")
    col1, col2 = st.columns(2)
    with col1:
        st.text("Top Keywords (keyword: score)")
        for word, score in top_k_words:
            st.write(f"{word}: {score:.2f}")
    with col2:
        st.text("Latest Tweets")
        st.dataframe(tweets)

sentiment_container = st.container()
with sentiment_container:
    st.subheader("Sentiment")
    st.info("Data for 10 minute intervals")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Positive Tweets", value=sentiment_time_series.iloc[-1]["Positive"]
        )
    with col2:
        st.metric(
            label="Negative Tweets", value=sentiment_time_series.iloc[-1]["Negative"]
        )
    with col3:
        st.metric(label="Ratio", value=f"{sentiment_time_series.iloc[-1]['Ratio']:.2%}")
    st.text("Sentiment Over Time")
    st.pyplot(sentiment_time_series_chart, use_container_width=False)


google_trends_container = st.container()
with google_trends_container:
    st.subheader("Google Trends")
    components.html(
        read_html_file(GOOGLE_TRENDS_CHARTS_URANIUM), height=500, width=1400
    )
    components.html(
        read_html_file(GOOGLE_TRENDS_CHARTS_NUCLEAR), height=500, width=1400
    )


stocks_container = st.container()
with stocks_container:
    st.subheader("Stock Charts")
    components.html(read_html_file(TRADINGVIEW_STOCK_CHARTS), height=500, width=1400)

time.sleep(2)
st.rerun()
