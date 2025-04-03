import os
from datetime import datetime, timezone

import spotipy
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from spotipy.oauth2 import SpotifyOAuth

from models import User, db

# Load environment variables
load_dotenv()

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

# Index name to search in
INDEX_NAME = "my_documents"

# Initialize database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Route for the home page with search form
@app.route("/")
@login_required
def home():
    return render_template("index.html")


# Route for search results
@app.route("/search")
@login_required
def search():
    # Get the search query from the request parameters
    query = request.args.get("q", "")

    if not query:
        return jsonify({"tracks": [], "albums": [], "artists": []})

    try:
        # Create Spotify client with user's token
        sp = spotipy.Spotify(auth=current_user.spotify_token)

        # Search tracks
        track_results = sp.search(q=query, type="track", limit=5)
        tracks = [
            {
                "id": track["id"],
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "album": track["album"]["name"],
                "image": (
                    track["album"]["images"][0]["url"]
                    if track["album"]["images"]
                    else None
                ),
                "preview_url": track["preview_url"],
                "external_url": track["external_urls"]["spotify"],
            }
            for track in track_results["tracks"]["items"]
        ]

        # Search albums
        album_results = sp.search(q=query, type="album", limit=5)
        albums = [
            {
                "id": album["id"],
                "name": album["name"],
                "artist": album["artists"][0]["name"],
                "image": album["images"][0]["url"] if album["images"] else None,
                "external_url": album["external_urls"]["spotify"],
            }
            for album in album_results["albums"]["items"]
        ]

        # Search artists
        artist_results = sp.search(q=query, type="artist", limit=5)
        artists = [
            {
                "id": artist["id"],
                "name": artist["name"],
                "image": artist["images"][0]["url"] if artist["images"] else None,
                "genres": artist["genres"],
                "external_url": artist["external_urls"]["spotify"],
            }
            for artist in artist_results["artists"]["items"]
        ]

        return jsonify({"tracks": tracks, "albums": albums, "artists": artists})

    except Exception as e:
        print(f"Error during search: {str(e)}")
        # Token might be expired, clear it and redirect to login
        current_user.spotify_token = None
        db.session.commit()
        return jsonify({"error": "Authentication error. Please log in again."}), 401


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

        result = {
            "track_name": track_name,
            "artist_name": artist_name,
            "image": image,
            "is_playing": is_playing,
            "progress": progress,
            "duration": duration,
        }
        return jsonify(result)
    except Exception as e:
        print(f"Error getting currently playing: {str(e)}")
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
        print(f"Error toggling playback: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/next-track", methods=["POST"])
@login_required
def next_track():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        sp.next_track()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error skipping to next track: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/previous-track", methods=["POST"])
@login_required
def previous_track():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        sp.previous_track()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error going to previous track: {str(e)}")
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
        print(f"Error setting volume: {str(e)}")
        return jsonify({"error": "Failed to set volume"}), 401


@app.route("/top-tracks")
@login_required
def get_top_tracks():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.current_user_top_tracks(limit=6, time_range="short_term")
        items = results["items"]

        results = sp.current_user_top_tracks(limit=6, time_range="medium_term")
        items += results["items"]

        results = sp.current_user_top_tracks(limit=6, time_range="long_term")
        items += results["items"]

        tracks = [
            {
                "id": track["id"],
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "album": track["album"]["name"],
                "image": (
                    track["album"]["images"][0]["url"]
                    if track["album"]["images"]
                    else None
                ),
                "preview_url": track["preview_url"],
                "external_url": track["external_urls"]["spotify"],
            }
            for track in items
        ]

        return jsonify({"tracks": tracks[:8]})
    except Exception as e:
        print(f"Error fetching top tracks: {str(e)}")
        return jsonify({"error": "Failed to fetch top tracks"}), 401


@app.route("/top-artists")
@login_required
def get_top_artists():
    try:
        sp = spotipy.Spotify(auth=current_user.spotify_token)
        results = sp.current_user_top_artists(limit=3, time_range="short_term")
        items = results["items"]

        results = sp.current_user_top_artists(limit=3, time_range="medium_term")
        items += results["items"]

        results = sp.current_user_top_artists(limit=3, time_range="long_term")
        items += results["items"]

        artists = [
            {
                "id": artist["id"],
                "name": artist["name"],
                "image": artist["images"][0]["url"] if artist["images"] else None,
                "genres": artist["genres"],
                "external_url": artist["external_urls"]["spotify"],
            }
            for artist in items
        ]

        return jsonify({"artists": artists[:4]})
    except Exception as e:
        print(f"Error fetching top artists: {str(e)}")
        return jsonify({"error": "Failed to fetch top artists"}), 401


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:5000/callback",
        scope="user-read-email user-read-private user-read-currently-playing user-modify-playback-state user-top-read",
    )


if __name__ == "__main__":
    # Create database tables
    with app.app_context():
        db.create_all()

    # Run the Flask app
    app.run(debug=True)
