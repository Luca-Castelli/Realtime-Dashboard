import re
from typing import List

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer

nltk.download("stopwords")
nltk.download("wordnet")


def preprocess_text(text: str) -> str:
    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    # Remove URLs
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    # Remove user mentions
    text = re.sub(r"\@\w+", "", text)
    # Remove hashtags
    text = re.sub(r"\#\w+", "", text)
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Remove numbers
    text = re.sub(r"\d+", "", text)
    text = text.lower()
    text_tokens = text.split()
    text_tokens_filtered = [
        lemmatizer.lemmatize(word) for word in text_tokens if word not in stop_words
    ]
    processed_text = " ".join(text_tokens_filtered)
    return processed_text


def get_top_tfidf_words(texts: List[str], k: int = 5) -> list[str]:
    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    sum_tfidf = tfidf_matrix.sum(axis=0).A1
    feature_names = vectorizer.get_feature_names_out()
    word_scores = zip(feature_names, sum_tfidf)
    sorted_word_scores = sorted(word_scores, key=lambda x: x[1], reverse=True)
    top_words = sorted_word_scores[:k]
    return top_words
