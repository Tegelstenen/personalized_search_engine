import logging
import os
from datetime import datetime, timedelta, timezone

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
    create_song_query,
    process_song_results,
)
from src.metrics import SearchMetrics
from src.models import User, UserInteraction, db
from src.spotipy_utils import (
    format_album_data,
    format_artist_data,
    format_track_data,
    remove_duplicates,
)
from src.user_profile import UserProfileManager
from src.utils import get_track_lyrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)


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

# Add Spotify configuration
app.config["SPOTIFY_CLIENT_ID"] = SPOTIFY_CLIENT_ID
app.config["SPOTIFY_CLIENT_SECRET"] = SPOTIFY_CLIENT_SECRET
app.config["SPOTIFY_REDIRECT_URI"] = "http://127.0.0.1:5000/callback"
app.config["SPOTIFY_SCOPE"] = (
    "user-read-email user-read-private user-read-currently-playing user-modify-playback-state user-top-read user-read-playback-state"
)

client = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", ES_LOCAL_PASSWORD),
)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


user_profile_manager = UserProfileManager()

search_metrics = SearchMetrics()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/search")
@login_required
def search():
    """Handle search requests for songs."""
    query = request.args.get("q", "")

    if not query:
        return jsonify({"hits": []})

    session_id = search_metrics.start_search_session(current_user.id, query)

    user_profile_manager.track_interaction(
        user_id=current_user.id,
        interaction_type="search",
        item_text=query,
        item_type="song",
    )

    personalized_query_vector = user_profile_manager.get_personalized_search_query(
        current_user.id, query
    )

    song_results = client.search(
        index="songs", body=create_song_query(query, personalized_query_vector)
    )
    hits = [process_song_results(hit) for hit in song_results["hits"]["hits"]]

    cleaned_hits = clean_and_deduplicate_results(hits)

    return jsonify({"hits": cleaned_hits, "session_id": session_id})


@app.route("/track-click", methods=["POST"])
@login_required
def track_click():
    try:
        data = request.get_json()
        item_text = data.get("item_text")
        item_type = data.get("item_type", "song")
        interaction_type = data.get("interaction_type", "click")

        if not item_text:
            return jsonify({"error": "Missing required fields"}), 400

        # If this is a like interaction, make sure we set the interaction_type to "like"
        if interaction_type == "like":
            interaction_type = "like"
            logger.info(f"Tracking like interaction: {item_text}")

        updated_metrics = search_metrics.track_interaction(
            user_id=current_user.id,
            interaction_type=interaction_type,
            item_text=item_text,
            item_type=item_type,
        )

        return jsonify({"status": "success", "latest_metrics": updated_metrics or {}})
    except Exception as e:
        logger.error(f"Error tracking click: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/track-play/<track_id>", methods=["POST"])
@login_required
def track_play(track_id):
    if not track_id:
        return jsonify({"success": False, "error": "No track ID provided"})

    try:
        data = request.json
        duration = data.get("duration", 0)
        item_text = data.get("item_text", "")  # Get item_text from request data

        # Only try to get track info if item_text is not provided
        if not item_text:
            try:
                sp = get_spotify_client()
                track_info = sp.track(track_id)

                track_name = track_info["name"]
                artist_name = track_info["artists"][0]["name"]
                album_name = track_info["album"]["name"]

                item_text = f"{track_name} by {artist_name} from {album_name}"
                app.logger.info(f"Successfully retrieved track info: {item_text}")
            except Exception as e:
                app.logger.error(f"Error getting track info for {track_id}: {str(e)}")
                # If we can't get track info, use a fallback item_text
                item_text = f"Track {track_id}"
                app.logger.warning(f"Using fallback item_text: {item_text}")

        # Track the play interaction with the search metrics service
        search_metrics.track_interaction(
            user_id=current_user.id,
            interaction_type="play",
            item_text=item_text,
            item_type="song",
            duration=duration,
        )

        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Error tracking play: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/get-track-info/<track_id>", methods=["GET"])
@login_required
def get_track_info(track_id):
    try:
        sp = get_spotify_client()
        track_info = sp.track(track_id)

        formatted_track = {
            "id": track_info["id"],
            "title": track_info["name"],
            "artist": track_info["artists"][0]["name"],
            "album": track_info["album"]["name"],
            "image": (
                track_info["album"]["images"][0]["url"]
                if track_info["album"]["images"]
                else None
            ),
            "preview_url": track_info.get("preview_url"),
            "external_url": track_info["external_urls"].get("spotify"),
        }

        return jsonify({"success": True, "track": formatted_track})
    except Exception as e:
        app.logger.error(f"Error getting track info: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


# Helper function to get Spotify client
def get_spotify_client():
    if (
        current_user.spotify_token_expiry
        and current_user.spotify_token_expiry < datetime.now()
    ):
        # Token expired, refresh it
        token_info = spotipy.SpotifyOAuth(
            client_id=app.config["SPOTIFY_CLIENT_ID"],
            client_secret=app.config["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=app.config["SPOTIFY_REDIRECT_URI"],
            scope=app.config["SPOTIFY_SCOPE"],
        ).refresh_access_token(current_user.spotify_refresh_token)

        current_user.spotify_token = token_info["access_token"]
        current_user.spotify_token_expiry = datetime.now() + timedelta(
            seconds=token_info["expires_in"]
        )
        db.session.commit()

    return spotipy.Spotify(auth=current_user.spotify_token)


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

    token_info = sp_oauth.get_access_token(code)

    sp = spotipy.Spotify(auth=token_info["access_token"])
    spotify_profile = sp.current_user()
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


@app.route("/dashboard")
@login_required
def dashboard():
    """Show the metrics dashboard."""
    # Get user metrics
    user_metrics = search_metrics.get_user_metrics(current_user.id)
    metrics_over_time = search_metrics.get_all_session_metrics(current_user.id)
    most_played_song = search_metrics.get_most_played_song(current_user.id)
    most_liked_album = search_metrics.get_most_liked_album(current_user.id)
    most_liked_artist = search_metrics.get_most_liked_artist(current_user.id)

    # If it's an AJAX request, return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "total_searches": user_metrics["search_count"],
                "total_interactions": user_metrics["interaction_count"],
                "metrics_over_time": metrics_over_time,
                "most_played_song": most_played_song,
                "most_liked_album": most_liked_album,
                "most_liked_artist": most_liked_artist,
            }
        )

    # Otherwise render the template
    return render_template(
        "dashboard.html",
        total_searches=user_metrics["search_count"],
        total_interactions=user_metrics["interaction_count"],
        metrics_over_time=metrics_over_time,
        most_played_song=most_played_song,
        most_liked_album=most_liked_album,
        most_liked_artist=most_liked_artist,
        current_time=datetime.now().strftime("%H:%M:%S"),
    )


@app.route("/latest-metrics")
@login_required
def latest_metrics():
    """Get the latest metrics for the dashboard."""
    try:
        # Add cache busting using query timestamp
        cache_buster = request.args.get("_", "")
        app.logger.info(f"Fetching latest metrics with cache buster: {cache_buster}")

        # Get metrics over time for chart
        metrics_over_time = search_metrics.get_all_session_metrics(current_user.id)

        # Get user metrics summary
        user_metrics = search_metrics.get_user_metrics(current_user.id)

        # Fetch the most played song directly from the database to ensure freshness
        most_played_song = search_metrics.get_most_played_song(current_user.id)
        app.logger.info(f"Most played song data: {most_played_song}")

        # Get most liked album and artist
        most_liked_album = search_metrics.get_most_liked_album(current_user.id)
        most_liked_artist = search_metrics.get_most_liked_artist(current_user.id)

        # Force database refresh to ensure latest data
        db.session.commit()

        return jsonify(
            {
                "metrics_over_time": metrics_over_time,
                "total_searches": user_metrics.get("search_count", 0),
                "total_interactions": user_metrics.get("interaction_count", 0),
                "most_played_song": most_played_song,
                "most_liked_album": most_liked_album,
                "most_liked_artist": most_liked_artist,
            }
        )
    except Exception as e:
        app.logger.error(f"Error fetching metrics: {str(e)}")
        return jsonify({"error": "Failed to fetch metrics", "message": str(e)}), 500


@app.route("/update-precision", methods=["POST"])
@login_required
def update_precision():
    try:
        data = request.get_json()
        precision5 = data.get("precision5", 0.0)
        precision10 = data.get("precision10", 0.0)
        session_id = data.get("session_id")

        if not session_id:
            return jsonify({"error": "Missing session ID"}), 400

        search_metrics.update_session_precision(
            session_id=session_id, precision5=precision5, precision10=precision10
        )

        return jsonify(
            {"status": "success", "precision5": precision5, "precision10": precision10}
        )
    except Exception as e:
        logger.error(f"Error updating precision: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/reset-app", methods=["POST"])
@login_required
def reset_app():
    try:
        # Reset all metrics for the current user
        search_metrics._reset_user_metrics(current_user.id)

        # Return success response
        return jsonify({"success": True})
    except Exception as e:
        # Log the error and return failure response
        app.logger.error(f"Error in reset_app: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
