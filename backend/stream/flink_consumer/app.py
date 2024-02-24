import os
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Tuple

import redis
from pydantic import BaseModel
from pyflink.common import Configuration
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.datastream.functions import MapFunction
from pyflink.datastream.window import Time, TumblingProcessingTimeWindows


@dataclass
class RedisConfig:
    host = os.getenv("REDIS_HOST")
    port = int(os.getenv("REDIS_PORT"))
    db = int(os.getenv("REDIS_DB"))


class Tweet(BaseModel):
    id: str
    user: str
    text: str
    created_at: str
    sentiment: str


class BaseRedisWriter(MapFunction):
    def __init__(self, redis_config: RedisConfig) -> None:
        self.redis_config = redis_config

    def open(self, context) -> None:
        self.redis = redis.Redis(
            host=self.redis_config.host,
            port=self.redis_config.port,
            db=self.redis_config.db,
        )

    @abstractmethod
    def map(self, value) -> Any:
        pass

    def close(self) -> None:
        self.redis.close()


class SentimentRedisWriter(BaseRedisWriter):
    def __init__(self, redis_config: RedisConfig) -> None:
        super().__init__(redis_config)
        self.positive_key = "positive_series"
        self.negative_key = "negative_series"

    def map(self, sentiment_count: Tuple[str, int]) -> None:
        sentiment, count = sentiment_count
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = f"{timestamp},{count}"
        if sentiment == "positive":
            self.redis.rpush(self.positive_key, data)
        else:
            self.redis.rpush(self.negative_key, data)


class FullTweetRedisWriter(BaseRedisWriter):
    def __init__(self, redis_config: RedisConfig) -> None:
        super().__init__(redis_config)
        self.key = "tweets"

    def map(self, tweet: Tweet) -> None:
        tweet_json = tweet.json()
        self.redis.rpush(self.key, tweet_json)


class JsonStringToTweetMapFunction(MapFunction):
    def map(self, tweets_str: str) -> Tweet:
        return Tweet.parse_raw(tweets_str)


class SentimentCounter(MapFunction):
    def map(self, tweet: Tweet) -> Tuple[str, int]:
        return (tweet.sentiment, 1)


def get_flink_environment(jar_files: List[str]) -> Any:
    env_config = Configuration()
    env_config.set_string("pipeline.jars", ";".join(jar_files))
    return StreamExecutionEnvironment.get_execution_environment(env_config)


def get_kafka_consumer(
    topics: str, bootstrap_servers: str, group_id: str, deserialization_schema: Any
) -> FlinkKafkaConsumer:
    properties = {"bootstrap.servers": bootstrap_servers, "group.id": group_id}
    return FlinkKafkaConsumer(
        topics=topics,
        deserialization_schema=deserialization_schema,
        properties=properties,
    )


def main():

    # Flink requires certain JAR files to consume from Kafka https://search.maven.org/
    # Make sure to get compatible versions of PyFlink, Kafka, and JARs (they all need
    # to line up properly)
    jar_files = [
        "file:///app/flink-sql-connector-kafka.jar",
        "file:///app/kafka-clients.jar",
    ]
    env = get_flink_environment(jar_files)

    kafka_consumer = get_kafka_consumer(
        topics="tweets_topic",
        bootstrap_servers="kafka:9093",
        group_id="tweet-consumer-group",
        deserialization_schema=SimpleStringSchema(),
    )

    # We are consuming JSON strings from Kafka, but we want to convert them to Tweet objects
    tweets_str = env.add_source(kafka_consumer)
    tweets = tweets_str.map(JsonStringToTweetMapFunction())

    sentiment_counts = (
        tweets.map(SentimentCounter())
        .key_by(lambda x: x[0])
        .window(TumblingProcessingTimeWindows.of(Time.seconds(10)))
        .reduce(lambda a, b: (a[0], a[1] + b[1]))
    )

    redis_config = RedisConfig()
    tweets.map(FullTweetRedisWriter(redis_config)).name("WriteFullTweetsToRedis")
    sentiment_counts.map(SentimentRedisWriter(redis_config)).name(
        "WriteSentimentCountsToRedis"
    )

    env.execute("flink_consumer")


if __name__ == "__main__":
    main()
