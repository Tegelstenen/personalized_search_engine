# type: ignore

import logging
import os
from datetime import datetime, timezone

import spotipy
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sentence_transformers import SentenceTransformer
from spotipy.oauth2 import SpotifyOAuth

from src.elastic_utils import (
    clean_and_deduplicate_results,
    create_album_query,
    create_artist_query,
    create_song_query,
    process_album_results,
    process_artist_results,
    process_song_results,
)
from src.models import User, db
from src.spotipy_utils import (
    format_album_data,
    format_artist_data,
    format_track_data,
    remove_duplicates,
)
from src.user_profile import UserProfileManager
from src.utils import get_track_lyrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Elasticsearch + DB
ES_LOCAL_PASSWORD = os.environ.get("ES_LOCAL_PASSWORD")
SECRET_KEY = os.environ.get("SECRET_KEY")
assert ES_LOCAL_PASSWORD is not None
assert SECRET_KEY is not None

# Spotify
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
assert SPOTIFY_CLIENT_ID is not None
assert SPOTIFY_CLIENT_SECRET is not None

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Connect to Elasticsearch
# For local development
client = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", ES_LOCAL_PASSWORD),
)

# Initialize database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore

# Initialize user profile manager
user_profile_manager = UserProfileManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Route for the home page with search form
@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/search")
@login_required
def search():
    """Handle search requests across artists, albums, and songs."""
    query = request.args.get("q", "")
    filter_type = request.args.get("filter", "all")

    if not query:
        return jsonify({"hits": []})

    # Track the search interaction
    item_type = "all"
    if filter_type in ["artists", "songs", "albums"]:
        item_type = filter_type[:-1]

    user_profile_manager.track_interaction(
        user_id=current_user.id,
        interaction_type="search",
        item_text=query,
        item_type=item_type,
    )

    hits = []

    # Search based on filter type
    if filter_type in ["all", "artists"]:
        # Search and process artists
        artist_results = client.search(index="artists", body=create_artist_query(query))
        for hit in artist_results["hits"]["hits"]:
            hits.extend(process_artist_results(hit))

    if filter_type in ["all", "albums"]:
        # Search and process albums
        album_results = client.search(index="albums", body=create_album_query(query))
        hits.extend(process_album_results(hit) for hit in album_results["hits"]["hits"])

    if filter_type in ["all", "songs"]:
        # Get personalized query embedding
        personalized_query_vector = user_profile_manager.get_personalized_search_query(
            current_user.id, query
        )

        # Search and process songs
        song_results = client.search(
            index="songs", body=create_song_query(query, personalized_query_vector)
        )
        hits.extend(process_song_results(hit) for hit in song_results["hits"]["hits"])

    # Clean and deduplicate results
    cleaned_hits = clean_and_deduplicate_results(hits)

    return jsonify({"hits": cleaned_hits})


@app.route("/track-click", methods=["POST"])
@login_required
def track_click():
    """Track when a user clicks on an item."""
    try:
        # Get item_text if provided in request body
        data = request.get_json() or {}
        item_text = data.get("item_text")
        item_type = data.get("item_type", "")

        if not item_text:
            raise ValueError("item_text is required for embedding")

        user_profile_manager.track_interaction(
            user_id=current_user.id,
            interaction_type="click",
            item_text=item_text,
            item_type=item_type,
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error tracking click: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/track-play/<track_id>", methods=["POST"])
@login_required
def track_play(track_id):
    """Track when a user plays a track."""
    duration = request.json.get("duration", 0)

    # Get track details from Spotify
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        track = sp.track(track_id)
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]
        album_name = track["album"]["name"]
        lyrics = get_track_lyrics(artist_name, track_name)
        if lyrics:
            # Format: track info + first few lines of lyrics
            lyrics_preview = lyrics.split("\n")[:5]  # First 5 lines only
            lyrics_text = " | ".join(
                line.strip() for line in lyrics_preview if line.strip()
            )
            item_text = (
                f"{track_name} by {artist_name} from {album_name} | {lyrics_text}"
            )

            # Truncate if it's too long
            if len(item_text) > 450:  # Keep within reasonable length
                item_text = item_text[:450] + "..."
        else:
            item_text = f"{track_name} by {artist_name} from {album_name}"

        user_profile_manager.track_interaction(
            user_id=current_user.id,
            interaction_type="play",
            duration=duration,
            item_text=item_text,
            item_type="song",
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error tracking play: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route for login
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/spotify-login")
def spotify_login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def spotify_callback():
    sp_oauth = create_spotify_oauth()
    code = request.args.get("code")

    if not code:
        return redirect(url_for("login"))

    # Exchange code for token information
    token_info = sp_oauth.get_access_token(code)

    # Get user's Spotify profile
    sp = spotipy.Spotify(auth=token_info["access_token"])
    spotify_profile = sp.current_user()
    # Find or create user
    user = User.query.filter_by(spotify_id=spotify_profile["id"]).first()
    if not user:
        user = User(
            spotify_id=spotify_profile["id"],
            display_name=spotify_profile["display_name"],
            email=spotify_profile.get("email"),
            profile_image=(
                spotify_profile.get("images")[0].get("url")
                if spotify_profile.get("images")
                else None
            ),
        )
        db.session.add(user)

    # Update user's Spotify information
    user.spotify_token = token_info["access_token"]
    user.spotify_refresh_token = token_info["refresh_token"]
    user.spotify_token_expiry = datetime.fromtimestamp(
        token_info["expires_at"], tz=timezone.utc
    )
    db.session.commit()
    login_user(user)

    return redirect(url_for("home"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/currently-playing")
@login_required
def currently_playing():
    result = {
        "track_name": None,
        "artist_name": None,
        "image": None,
        "is_playing": False,
        "progress": 0,
        "duration": 0,
        "track_id": None,
    }
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        current_track = sp.currently_playing()

        if current_track is None:
            return jsonify(result)

        track_name = current_track.get("item", {}).get("name", "Unknown")
        artist_name = (
            current_track.get("item", {}).get("artists", [{}])[0].get("name", "Unknown")
        )
        image = (
            current_track.get("item", {})
            .get("album", {})
            .get("images", [{}])[0]
            .get("url", None)
        )
        is_playing = current_track.get("is_playing", False)
        progress = current_track.get("progress_ms", 0)
        duration = current_track.get("item", {}).get("duration_ms", 0)
        track_id = current_track.get("item", {}).get("id", None)

        result = {
            "track_name": track_name,
            "artist_name": artist_name,
            "image": image,
            "is_playing": is_playing,
            "progress": progress,
            "duration": duration,
            "track_id": track_id,
        }
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting currently playing: {str(e)}")
        return jsonify(result), 401


@app.route("/toggle-playback", methods=["POST"])
@login_required
def toggle_playback():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        current_playback = sp.currently_playing()

        if current_playback and current_playback.get("is_playing"):
            sp.pause_playback()
        else:
            sp.start_playback()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error toggling playback: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/next-track", methods=["POST"])
@login_required
def next_track():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        sp.next_track()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error skipping to next track: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/previous-track", methods=["POST"])
@login_required
def previous_track():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        sp.previous_track()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error going to previous track: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/set-volume", methods=["POST"])
@login_required
def set_volume():
    try:
        volume_percent = request.json.get("volume")
        if volume_percent is None or not isinstance(volume_percent, int):
            return jsonify({"error": "Invalid volume value"}), 400

        volume_percent = max(
            0, min(100, volume_percent)
        )  # Ensure volume is between 0-100
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        sp.volume(volume_percent)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error setting volume: {str(e)}")
        return jsonify({"error": "Failed to set volume"}), 401


@app.route("/top-tracks")
@login_required
def get_top_tracks():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        items = []

        for time_range in ["short_term", "medium_term", "long_term"]:
            results = sp.current_user_top_tracks(limit=6, time_range=time_range)
            items.extend(results["items"])

        tracks = [format_track_data(track) for track in items]
        tracks = remove_duplicates(tracks)

        return jsonify({"tracks": tracks[:8]})
    except Exception as e:
        logger.error(f"Error fetching top tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch top tracks"}), 401


@app.route("/top-artists")
@login_required
def get_top_artists():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        items = []

        for time_range in ["short_term", "medium_term", "long_term"]:
            results = sp.current_user_top_artists(limit=3, time_range=time_range)
            items.extend(results["items"])

        artists = [format_artist_data(artist) for artist in items]
        artists = remove_duplicates(artists)
        return jsonify({"artists": artists[:4]})
    except Exception as e:
        logger.error(f"Error fetching top artists: {str(e)}")
        return jsonify({"error": "Failed to fetch top artists"}), 401


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:5000/callback",
        scope="user-read-email user-read-private user-read-currently-playing user-modify-playback-state user-top-read user-read-playback-state",
    )


@app.route("/artist-songs/<artist_name>")
@login_required
def get_artist_songs(artist_name):
    """Get top songs for a specific artist using Spotify API."""
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.search(q=artist_name, type="artist", limit=1)

        if not results["artists"]["items"]:
            return jsonify({"error": "Artist not found"}), 404

        artist_id = results["artists"]["items"][0]["id"]
        top_tracks = sp.artist_top_tracks(artist_id)
        tracks = [format_track_data(track) for track in top_tracks["tracks"][:3]]
        return jsonify({"tracks": tracks})
    except Exception as e:
        logger.error(f"Error getting artist songs from Spotify: {str(e)}")
        return jsonify({"error": "Failed to fetch artist songs"}), 500


@app.route("/play-track", methods=["POST"])
@login_required
def play_track():
    try:
        data = request.get_json()
        track_id = data.get("track_id")

        if not track_id:
            return jsonify({"error": "No track ID provided"}), 400

        sp = spotipy.Spotify(auth=current_user.spotify_token)

        devices = sp.devices()
        if not devices["devices"]:
            return jsonify({"error": "No active Spotify devices found"}), 400

        device_id = devices["devices"][0]["id"]
        sp.start_playback(device_id=device_id, uris=[f"spotify:track:{track_id}"])
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Error playing track: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-spotify-track/<track_id>")
@login_required
def get_spotify_track(track_id):
    """Get a specific track from Spotify by its ID."""
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        track = sp.track(track_id)
        track_data = format_track_data(track)
        return jsonify({"track": track_data})
    except Exception as e:
        logger.error(f"Error getting Spotify track: {str(e)}")
        return jsonify({"error": "Failed to fetch Spotify track"}), 500


@app.route("/search-spotify-tracks/<title>")
@login_required
def search_spotify_tracks(title):
    """Search for tracks on Spotify by title and return top 3 matches."""
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.search(q=title, type="track", limit=3)
        tracks = [format_track_data(track) for track in results["tracks"]["items"]]
        return jsonify({"tracks": tracks})
    except Exception as e:
        logger.error(f"Error searching Spotify tracks: {str(e)}")
        return jsonify({"error": "Failed to search Spotify tracks"}), 500


@app.route("/search-spotify-artist/<artist_name>")
@login_required
def search_spotify_artist(artist_name):
    """Search for an artist on Spotify and return the best match."""
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.search(q=artist_name, type="artist", limit=1)

        if not results["artists"]["items"]:
            return jsonify({"error": "Artist not found"}), 404

        artist = results["artists"]["items"][0]
        artist_data = format_artist_data(artist)
        return jsonify({"artist": artist_data})
    except Exception as e:
        logger.error(f"Error searching Spotify artist: {str(e)}")
        return jsonify({"error": "Failed to search Spotify artist"}), 500


@app.route("/search-spotify-album/<path:query>")
@login_required
def search_spotify_album(query):
    """Search for an album on Spotify and return the best match."""
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.search(q=query, type="album", limit=1)

        if not results["albums"]["items"]:
            return jsonify({"error": "Album not found"}), 404

        album = results["albums"]["items"][0]
        album_data = format_album_data(album)
        return jsonify({"album": album_data})
    except Exception as e:
        logger.error(f"Error searching Spotify album: {str(e)}")
        return jsonify({"error": "Failed to search Spotify album"}), 500


if __name__ == "__main__":
    # Create database tables
    with app.app_context():
        db.create_all()

    # Run the Flask app
    app.run(debug=True)
