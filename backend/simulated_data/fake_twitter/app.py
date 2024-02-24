import csv
import datetime
import json
import random
import time
from typing import Generator, List

from faker import Faker
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import StreamingResponse

app = FastAPI(title="Fake Twitter API")
fake = Faker()


FAKE_TWEET_TEXT_PATH = "fake_tweet_text.csv"


class Tweet(BaseModel):
    id: str
    user: str
    text: str
    created_at: str


def generate_fake_tweet_text() -> List[str]:
    # Data contained in FAKE_TWEET_TEXT_PATH was generated using ChatGPT
    # I didn't use Faker since I want custom tweet text pertaining to Uranium/Nuclear
    fake_tweet_text = []
    with open(FAKE_TWEET_TEXT_PATH) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            fake_tweet_text.append(row[0])
    return fake_tweet_text


def generate_fake_tweets() -> Generator[Tweet, None, None]:
    # All Tweet data except for text is generated using Faker
    fake_tweet_text = generate_fake_tweet_text()
    while True:
        fake_tweet = Tweet(
            id=fake.uuid4(),
            user=fake.user_name(),
            text=random.choice(fake_tweet_text),
            created_at=str(datetime.datetime.now()),
        )
        yield fake_tweet
        # Sleeping to simulate delay between Tweets
        time.sleep(random.uniform(1, 20))


@app.get("/v1/tweet-stream", tags=["Tweets"])
async def stream_fake_tweets() -> StreamingResponse:
    """
    Streams a live feed of fake tweets in real-time using Server-Sent Events (SSE).

    **Response Format:**
    ```
    data: {"id": "unique_id", "user": "username", "text": "tweet text", "created_at": "YYYY-MM-DDTHH:MM:SS"}
    ```
    **Usage:** Clients should listen for events on this endpoint to receive live updates. Each event received corresponds to a new fake tweet.

    **Note:** This endpoint is for demonstration purposes and generates synthetic tweet data.
    """

    def event_stream() -> Generator[str, None, None]:
        for fake_tweet in generate_fake_tweets():
            fake_tweet_json = json.dumps(fake_tweet.dict())
            # Both the data keyword and \n\n are required for Server-Sent Events (SSE)
            yield f"data: {fake_tweet_json}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
