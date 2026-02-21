"""
Spotify API Enrichment

Fetches track metadata and artist genres from the Spotify API
based on unique track URIs.
"""

import os
import time
import logging
from typing import List, Dict, Optional, Tuple

import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# =========================
# Configuration
# =========================

INPUT_FILE = "spotify_charts_master.csv"
OUTPUT_FILE = "spotify_enriched_tracks.csv"
BATCH_SIZE = 50  # Spotify API limit


# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# Authentication
# =========================

def authenticate_spotify() -> spotipy.Spotify:
    """
    Authenticate using environment variables:
    SPOTIFY_CLIENT_ID
    SPOTIFY_CLIENT_SECRET
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "Spotify credentials not found. "
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET as environment variables."
        )

    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )

    return spotipy.Spotify(auth_manager=auth_manager)


# =========================
# Utility Functions
# =========================

def extract_track_id(uri: str) -> Optional[str]:
    """Extract track ID from Spotify URI."""
    if pd.isna(uri) or not isinstance(uri, str):
        return None

    if uri.startswith("spotify:track:"):
        return uri.replace("spotify:track:", "")
    if len(uri) == 22:
        return uri

    return None


def batch_items(items: List[str], batch_size: int):
    """Yield successive batches."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def fetch_tracks(sp: spotipy.Spotify, track_ids: List[str]) -> Dict[str, Dict]:
    """Fetch track metadata."""
    results = sp.tracks(track_ids)

    output = {}

    for index, track in enumerate(results["tracks"]):
        track_id = track_ids[index]

        if track is None:
            output[track_id] = {}
            continue

        album = track.get("album", {})

        output[track_id] = {
            "duration_ms": track.get("duration_ms"),
            "duration_sec": (
                track.get("duration_ms") / 1000
                if track.get("duration_ms") else None
            ),
            "popularity": track.get("popularity"),
            "explicit": track.get("explicit"),
            "album_release_date": album.get("release_date"),
            "album_type": album.get("album_type"),
            "album_cover_url": (
                album.get("images")[0]["url"]
                if album.get("images")
                else None
            ),
            "artist_ids": [a["id"] for a in track.get("artists", []) if a.get("id")]
        }

    return output


def fetch_artist_genres(sp: spotipy.Spotify, artist_ids: List[str]) -> Dict[str, List[str]]:
    """Fetch artist genres."""
    results = sp.artists(artist_ids)

    return {
        artist_ids[i]: artist.get("genres", []) if artist else []
        for i, artist in enumerate(results["artists"])
    }


# =========================
# Main Pipeline
# =========================

def main():

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"{INPUT_FILE} not found.")

    logging.info("Loading master dataset...")
    df = pd.read_csv(INPUT_FILE)

    if "uri" not in df.columns:
        raise ValueError("Input file must contain a 'uri' column.")

    unique_uris = df["uri"].dropna().unique().tolist()
    track_ids = [extract_track_id(uri) for uri in unique_uris]
    track_ids = [tid for tid in track_ids if tid]

    logging.info(f"Found {len(track_ids):,} unique tracks.")

    sp = authenticate_spotify()

    # Fetch track metadata
    all_tracks = {}
    for batch in batch_items(track_ids, BATCH_SIZE):
        all_tracks.update(fetch_tracks(sp, batch))
        time.sleep(0.2)

    logging.info("Track metadata fetched.")

    # Collect unique artist IDs
    artist_ids = list({
        artist_id
        for track in all_tracks.values()
        for artist_id in track.get("artist_ids", [])
    })

    all_artist_genres = {}
    for batch in batch_items(artist_ids, BATCH_SIZE):
        all_artist_genres.update(fetch_artist_genres(sp, batch))
        time.sleep(0.2)

    logging.info("Artist genres fetched.")

    # Build final dataframe
    records = []

    for uri in unique_uris:
        track_id = extract_track_id(uri)
        track_data = all_tracks.get(track_id, {})

        genres = []
        for artist_id in track_data.get("artist_ids", []):
            genres.extend(all_artist_genres.get(artist_id, []))

        genres = list(dict.fromkeys(genres))  # deduplicate

        record = {
            "uri": uri,
            **{k: v for k, v in track_data.items() if k != "artist_ids"},
            "artist_genres": ", ".join(genres) if genres else None
        }

        records.append(record)

    enriched_df = pd.DataFrame(records)

    enriched_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    logging.info("Enrichment complete.")
    logging.info(f"Output saved to {OUTPUT_FILE}")
    logging.info(f"Total tracks enriched: {len(enriched_df):,}")


if __name__ == "__main__":
    main()