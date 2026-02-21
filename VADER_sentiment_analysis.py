"""
VADER Sentiment Analysis Module

Computes lexicon-based sentiment metrics for song lyrics.

This script assumes lyrics are already present in the dataset.
"""

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
import os

# Configuration
INPUT_FILE = "lyrics_dataset.csv"
OUTPUT_FILE = "lyrics_with_vader_sentiment.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

analyzer = SentimentIntensityAnalyzer()


def calculate_sentiment(text: str) -> float:
    """Return compound sentiment score (-1 to +1)."""
    if not isinstance(text, str) or not text.strip():
        return None
    scores = analyzer.polarity_scores(text)
    return scores["compound"]


def add_vader_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add sentiment metrics to dataframe."""
    logging.info("Calculating VADER sentiment scores...")

    df["sentiment_score"] = df["lyrics"].apply(calculate_sentiment)

    logging.info("✓ Sentiment calculation complete")
    return df


def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"{INPUT_FILE} not found")

    logging.info(f"Loading dataset: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    if "lyrics" not in df.columns:
        raise ValueError("Dataset must contain a 'lyrics' column")

    df = add_vader_metrics(df)

    logging.info(f"Saving results to {OUTPUT_FILE}")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    logging.info("✓ Done")


if __name__ == "__main__":
    main()