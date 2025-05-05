import re
from collections import defaultdict


def create_artist_query(query):
    """Create the Elasticsearch query for artists."""
    return {
        "query": {
            "bool": {
                "should": [
                    # Exact matches for artist name (highest priority)
                    {"term": {"name.keyword": {"value": query, "boost": 10}}},

                    # Phrase matches (high priority)
                    {"match_phrase": {"name": {"query": query, "boost": 5}}},

                    # Text field matches
                    {"match": {"name": {"query": query, "boost": 3, "fuzziness": "AUTO"}}},
                    {"match": {"nameVariations": {"query": query, "boost": 2}}},

                    # Lower priority matches
                    {"match": {"abstract": {"query": query, "boost": 1}}},
                    {"match": {"genres": {"query": query, "boost": 1}}},
                ],
                "minimum_should_match": 1
            }
        },
        "highlight": {
            "fields": {
                "name": {},
                "nameVariations": {},
                "abstract": {},
                "genres": {}
            }
        },
        "size": 30
    }


def create_album_query(query):
    """Create the Elasticsearch query for albums."""
    return {
        "query": {
            "bool": {
                "should": [
                    # Title matches (highest priority)
                    {"term": {"title.keyword": {"value": query, "boost": 10}}},
                    {"match_phrase": {"title": {"query": query, "boost": 8}}},
                    {"match": {"title": {"query": query, "boost": 5, "fuzziness": "AUTO"}}},

                    # Name matches (high priority)
                    {"term": {"name.keyword": {"value": query, "boost": 8}}},
                    {"match_phrase": {"name": {"query": query, "boost": 6}}},
                    {"match": {"name": {"query": query, "boost": 4, "fuzziness": "AUTO"}}},

                    # Artist name matches (medium priority)
                    {"term": {"artist_name.keyword": {"value": query, "boost": 3}}},
                    {"match_phrase": {"artist_name": {"query": query, "boost": 2}}},
                    {"match": {"artist_name": {"query": query, "boost": 1}}},
                ],
                "minimum_should_match": 1
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "name": {},
                "artist_name": {}
            }
        },
        "size": 30
    }


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
                "boost": 0.8
            },
            # comment this if lyrics embeddings are not available yet
            {
                "field": "lyrics_embedding",
                "query_vector": query_vector,
                "k": return_size,
                "num_candidates": 1000,
                "boost": 0.2
            }
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
            "rrf": {
                "rank_window_size": return_size
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "artist": {},
                "albumTitle": {}
            }
        },
        "size": return_size
    }


def process_artist_results(hit):
    """Process artist search results including nested member matches."""
    results = []
    source = hit["_source"]
    highlight = hit.get("highlight", {})
    inner_hits = (
        hit.get("inner_hits", {}).get("members", {}).get("hits", {}).get("hits", [])
    )

    # Process top-level artist match
    if highlight:
        title = highlight.get("name", [source.get("name", "Unknown")])[0]

        # Get genre information (prioritize highlighted version if available)
        genre_info = ""
        if "genres" in highlight:
            genre_info = highlight["genres"][0]
        elif "dbp_genre" in highlight:
            genre_info = highlight["dbp_genre"][0]
        elif "genres" in source:
            genre_info = ", ".join(source["genres"][:3]) if isinstance(source.get("genres"), list) else source.get(
                "genres", "")
        elif "dbp_genre" in source:
            genre_info = source.get("dbp_genre", "")

        # Get location information
        location_info = ""
        if "location" in source:
            location = source["location"]
            city = location.get("city", "")
            country = location.get("country", "")
            if city and country:
                location_info = f"{city}, {country}"
            elif city:
                location_info = city
            elif country:
                location_info = country

        # Get artist image
        image_url = None
        if "picture" in source:
            # Try to get image from picture field in descending size preference
            picture = source["picture"]
            image_url = (
                    picture.get("xl") or
                    picture.get("big") or
                    picture.get("standard") or
                    picture.get("medium") or
                    picture.get("small")
            )

        # Create a rich snippet with artist details
        rich_snippet = ""

        # Create a rich snippet combining abstract and metadata
        abstract = next(
            (
                highlight[field][0]
                for field in ["abstract", "dbp_abstract"]
                if field in highlight
            ),
            source.get("abstract", source.get("dbp_abstract", "")),
        )

        # Add genre information if available
        if genre_info:
            rich_snippet += genre_info

        # Add location information if available
        if location_info:
            if rich_snippet:
                rich_snippet += f" • {location_info}"
            else:
                rich_snippet += location_info

        # Add abstract information if available
        if abstract:
            if rich_snippet:
                rich_snippet += f" • {abstract[:150]}..." if len(abstract) > 150 else f" • {abstract}"
            else:
                rich_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract

        results.append(
            {
                "id": hit["_id"],
                "title": title,
                "content": rich_snippet,
                "image": image_url,
                "type": "artists",
                "score": hit["_score"],
                "source": source,
            }
        )

    # Process nested member matches
    for inner_hit in inner_hits:
        member = inner_hit["_source"]
        title = member.get("name", "Unknown Member")

        # Create a rich snippet for the member
        member_snippet = ""

        # Add member information
        if "dbp_abstract" in member:
            member_snippet = member["dbp_abstract"]
        elif "abstract" in member:
            member_snippet = member["abstract"]
        elif "nameVariations" in member and member["nameVariations"]:
            member_snippet = f"Also known as: {', '.join(member['nameVariations'])}"

        # Add parent artist information
        if source.get("name"):
            if member_snippet:
                member_snippet = f"Member of {source['name']} • {member_snippet[:150]}..." if len(
                    member_snippet) > 150 else f"Member of {source['name']} • {member_snippet}"
            else:
                member_snippet = f"Member of {source['name']}"

        results.append(
            {
                "id": f"{hit['_id']}_{inner_hit['_nested']['offset']}",
                "title": title,
                "content": member_snippet,
                "image": None,  # Members typically don't have separate images
                "type": "artists",
                "score": inner_hit["_score"],
                "source": {"member": member, "artist": source},
            }
        )

    return results


def process_album_results(hit):
    """Process album search results."""
    source = hit["_source"]
    highlight = hit.get("highlight", {})

    title = highlight.get(
        "title",
        highlight.get("name", [source.get("title", source.get("name", "Unknown"))]),
    )[0]

    # Get artist name (prioritize highlighted version if available)
    artist_name = ""
    if "artist_name" in highlight:
        artist_name = highlight["artist_name"][0]
    elif "artist_name" in source:
        artist_name = source["artist_name"]

    # Get genre information
    genre_info = ""
    if "genre" in highlight:
        genre_info = highlight["genre"][0]
    elif "genre" in source:
        genre_info = source["genre"]

    # Get year information
    year_info = source.get("year", "")

    # Get album cover image
    image_url = None
    if "cover" in source:
        # Try to get image from cover field in descending size preference
        cover = source["cover"]
        image_url = (
                cover.get("xl") or
                cover.get("big") or
                cover.get("standard") or
                cover.get("medium") or
                cover.get("small")
        )

    # Create a rich snippet with album details
    rich_snippet = ""

    # Add artist information if available
    if artist_name:
        rich_snippet += f"By {artist_name}"

    # Add year information if available
    if year_info:
        if rich_snippet:
            rich_snippet += f" • {year_info}"
        else:
            rich_snippet += f"{year_info}"

    # Add genre information if available
    if genre_info:
        if rich_snippet:
            rich_snippet += f" • {genre_info}"
        else:
            rich_snippet += genre_info

    # Add country information if available
    country_info = source.get("country", "")
    if country_info and rich_snippet:
        rich_snippet += f" • {country_info}"

    return {
        "id": hit["_id"],
        "title": title,
        "content": rich_snippet,
        "image": image_url,
        "type": "albums",
        "score": hit["_score"],
        "source": source,
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
            rich_snippet += f" • {content_snippet[:150]}..." if len(content_snippet) > 150 else f" • {content_snippet}"
        else:
            rich_snippet = content_snippet[:200] + "..." if len(content_snippet) > 200 else content_snippet

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
