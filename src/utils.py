import logging
import re

import requests

logger = logging.getLogger(__name__)


def get_track_lyrics(artist_name, track_name):
    """Get lyrics for a specific track."""
    try:
        # Clean up track and artist names for better API matching
        artist_name = (
            artist_name.replace("&", "and")
            .replace("feat.", "")
            .replace("ft.", "")
            .strip()
        )
        track_name = track_name.split("(")[0].split("-")[0].strip()

        # Try to fetch lyrics using a public lyrics API
        lyrics = None
        try:
            # Using lyrics.ovh API
            response = requests.get(
                f"https://api.lyrics.ovh/v1/{artist_name}/{track_name}", timeout=5
            )
            if response.status_code == 200:
                lyrics = response.json().get("lyrics")
                if lyrics:
                    # Remove excess whitespace and empty lines
                    lines = [line.strip() for line in lyrics.split("\n")]
                    lyrics = "\n".join(line for line in lines if line)
        except Exception as e:
            logger.error(f"Error fetching lyrics from API: {str(e)}")

        return lyrics
    except Exception as e:
        logger.error(f"Error processing lyrics: {str(e)}")
        return None


def remove_html_tags(text):
    """Remove HTML tags from text."""
    if not isinstance(text, str):
        return text
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)
