import re
from collections import defaultdict


def create_song_query(query, query_vector, return_size=100):
    """Create the Elasticsearch query for songs."""
    return {
        # vector search that matches title & lyrics
        "knn": [
            {
                "field": "title_embedding",
                "query_vector": query_vector,
                "k": return_size,
                "num_candidates": 5000,
                "boost": 0.8,
            },
            # comment this if lyrics embeddings are not available yet
            {
                "field": "lyrics_embedding",
                "query_vector": query_vector,
                "k": return_size,
                "num_candidates": 1000,
                "boost": 0.2,
            },
        ],
        # full-text search
        # "query": {
        #     "bool": {
        #         "should": [
        #             # Title matches (highest priority)
        #             {"term": {"title.keyword": {"value": query, "boost": 10}}},
        #             {"match_phrase": {"title": {"query": query, "boost": 8}}},
        #             {"match": {"title": {"query": query, "boost": 5, "fuzziness": "AUTO"}}},
        #
        #             # Artist matches (medium priority)
        #             {"term": {"artist.keyword": {"value": query, "boost": 3}}},
        #             {"match_phrase": {"artist": {"query": query, "boost": 2}}},
        #             {"match": {"artist": {"query": query, "boost": 1}}},
        #
        #             # Album title matches (lower priority)
        #             {"match_phrase": {"albumTitle": {"query": query, "boost": 1}}},
        #         ],
        #         "minimum_should_match": 1
        #     }
        # },
        "rank": {
            # combine full-text & vector search
            "rrf": {"rank_window_size": return_size}
        },
        "highlight": {"fields": {"title": {}, "artist": {}, "albumTitle": {}}},
        "size": return_size,
    }


def process_song_results(hit):
    """Process song search results."""
    source = hit["_source"]
    highlight = hit.get("highlight", {})

    title = highlight.get(
        "title",
        highlight.get("name", [source.get("title", source.get("name", "Unknown"))]),
    )[0]

    # Get artist name (prioritize highlighted version if available)
    artist_name = ""
    if "artist" in highlight:
        artist_name = highlight["artist"][0]
    elif "artist" in source:
        artist_name = source["artist"]

    # Get album title (prioritize highlighted version if available)
    album_title = ""
    if "albumTitle" in highlight:
        album_title = highlight["albumTitle"][0]
    elif "albumTitle" in source:
        album_title = source["albumTitle"]

    # Get preview URL if available
    preview_url = source.get("preview", None)

    # Create a richer snippet with song details
    rich_snippet = ""

    # Add artist information if available
    if artist_name:
        rich_snippet += f"By {artist_name}"

    # Add album information if available
    if album_title:
        if rich_snippet:
            rich_snippet += f" • Album: {album_title}"
        else:
            rich_snippet += f"Album: {album_title}"

    # Add lyrics/summary snippet if available
    content_snippet = next(
        (
            highlight[field][0]
            for field in ["lyrics", "summary", "album_genre"]
            if field in highlight
        ),
        source.get("lyrics", source.get("summary", source.get("album_genre", ""))),
    )

    if content_snippet:
        if rich_snippet:
            rich_snippet += (
                f" • {content_snippet[:150]}..."
                if len(content_snippet) > 150
                else f" • {content_snippet}"
            )
        else:
            rich_snippet = (
                content_snippet[:200] + "..."
                if len(content_snippet) > 200
                else content_snippet
            )

    return {
        "id": hit["_id"],
        "title": title,
        "content": rich_snippet,
        "preview": preview_url,
        "type": "songs",
        "score": hit["_score"],
        "source": source,
    }


def remove_html_tags(text):
    """Remove HTML tags from text."""
    if not isinstance(text, str):
        return text
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)


def clean_and_deduplicate_results(hits):
    """Clean HTML tags and deduplicate results by category."""
    seen_titles = defaultdict(set)
    cleaned_hits = []

    # First pass - clean and identify duplicates
    preprocessed = []
    for hit in hits:
        # Clean HTML tags from title and content
        hit["title"] = remove_html_tags(hit["title"])
        hit["content"] = remove_html_tags(hit["content"])

        # Retrieve titel, type and artist for hit
        hit_title = hit["title"].lower()
        hit_type = hit["type"]
        hit_artist = hit["source"]["name"].lower()

        # Create a key for deduplication ((title, artist))
        key = (hit_title, hit_artist)

        # If we haven't seen this title+artist for this type, add it
        if key not in seen_titles[hit_type]:
            seen_titles[hit_type].add(key)
            preprocessed.append(hit)

    # Sort all hits by score within their type
    artist_hits = [h for h in preprocessed if h["type"] == "artists"]
    album_hits = [h for h in preprocessed if h["type"] == "albums"]
    song_hits = [h for h in preprocessed if h["type"] == "songs"]

    # Sort each category by score
    artist_hits.sort(key=lambda x: x["score"], reverse=True)
    album_hits.sort(key=lambda x: x["score"], reverse=True)
    song_hits.sort(key=lambda x: x["score"], reverse=True)

    # Interleave results to create a more balanced display
    # Start with top hits of each type to ensure diversity
    for i in range(max(len(artist_hits), len(album_hits), len(song_hits))):
        if i < len(artist_hits):
            cleaned_hits.append(artist_hits[i])
        if i < len(album_hits):
            cleaned_hits.append(album_hits[i])
        if i < len(song_hits):
            cleaned_hits.append(song_hits[i])

    return cleaned_hits
