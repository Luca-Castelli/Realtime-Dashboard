import os

from openai import OpenAI

OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")

open_ai_client = OpenAI(api_key=OPEN_AI_KEY)


def random_sentiment_analyzer(text: str) -> str:
    if len(text) % 2 == 0:
        return "positive"
    else:
        return "negative"


def openai_davinci_sentiment_analyzer(text: str) -> str:

    response = open_ai_client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {
                "role": "user",
                "content": f"Analyze the sentiment of this text and return a single word: 'positive' or 'negative'. Text: {text}",
            }
        ],
        temperature=0.3,
        max_tokens=3,
    )
    return response.choices[0].message.content
