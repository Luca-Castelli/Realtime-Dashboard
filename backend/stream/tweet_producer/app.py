import json
from typing import Generator

import requests
from kafka import KafkaProducer
from pydantic import BaseModel
from sentiment_analysis import random_sentiment_analyzer


class Tweet(BaseModel):
    id: str
    user: str
    text: str
    created_at: str
    sentiment: str = None


def get_kafka_producer(bootstrap_servers: str) -> KafkaProducer:
    kafka_producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    return kafka_producer


def consume_tweet() -> Generator[Tweet, None, None]:
    response = requests.get("http://fake_twitter:8000/v1/tweet-stream", stream=True)
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            json_str = line[len(b"data: ") :].decode("utf-8").strip()
            tweet_data = json.loads(json_str)
            yield Tweet(**tweet_data)


def enrich_tweet(tweet: Tweet) -> Tweet:
    tweet.sentiment = random_sentiment_analyzer(tweet.text)
    return tweet


def produce_tweets(kafka_producer: KafkaProducer) -> None:
    for tweet in consume_tweet():
        tweet = enrich_tweet(tweet)
        kafka_producer.send("tweets_topic", tweet.dict())
        kafka_producer.flush()


if __name__ == "__main__":
    kafka_producer = get_kafka_producer("kafka:9093")
    produce_tweets(kafka_producer)
