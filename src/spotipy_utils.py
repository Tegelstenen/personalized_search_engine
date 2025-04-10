def format_track_data(track: dict) -> dict:
    return {
        "id": track["id"],
        "title": track["name"],
        "artist": track["artists"][0]["name"],
        "album": track["album"]["name"],
        "image": (
            track["album"]["images"][0]["url"] if track["album"]["images"] else None
        ),
        "preview_url": track.get("preview_url"),
        "external_url": track["external_urls"].get("spotify"),
    }


def format_album_data(album: dict) -> dict:
    return {
        "id": album["id"],
        "name": album["name"],
        "artist": album["artists"][0]["name"],
        "image": album["images"][0]["url"] if album["images"] else None,
        "release_date": album["release_date"],
        "total_tracks": album["total_tracks"],
        "external_url": album["external_urls"]["spotify"],
    }


def format_artist_data(artist: dict) -> dict:
    return {
        "id": artist["id"],
        "name": artist["name"],
        "image": artist["images"][0]["url"] if artist["images"] else None,
        "genres": artist["genres"],
        "followers": artist.get("followers", {}).get("total"),
        "popularity": artist.get("popularity"),
        "external_url": artist["external_urls"]["spotify"],
    }


def remove_duplicates(items: list) -> list:
    unique_items = {}
    for item in items:
        if item["id"] not in unique_items:
            unique_items[item["id"]] = item
    return list(unique_items.values())
