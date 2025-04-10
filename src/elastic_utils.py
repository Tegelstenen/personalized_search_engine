import re
from collections import defaultdict


def create_artist_query(query):
    """Create the Elasticsearch query for artists."""
    return {
        "query": {
            "bool": {
                "should": [
                    {
                        "nested": {
                            "path": "members",
                            "query": {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "members.name^3",
                                        "members.nameVariations^2",
                                        "members.abstract^2",
                                        "members.dbp_abstract",
                                        "members.type",
                                        "members.realName",
                                    ],
                                    "fuzziness": "AUTO",
                                }
                            },
                            "inner_hits": {},
                        }
                    },
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "name^3",
                                "nameVariations^2",
                                "abstract^2",
                                "dbp_abstract",
                                "dbp_genre",
                                "genres",
                                "type",
                                "location.city",
                                "location.country",
                            ],
                            "fuzziness": "AUTO",
                        }
                    },
                ]
            }
        },
        "highlight": {
            "fields": {
                "name": {},
                "nameVariations": {},
                "abstract": {},
                "dbp_abstract": {},
                "genres": {},
                "type": {},
            }
        },
    }


def create_album_query(query):
    """Create the Elasticsearch query for albums."""
    return {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "name^3", "genre^2", "country", "language"],
                "fuzziness": "AUTO",
            }
        },
        "highlight": {"fields": {"title": {}, "name": {}, "genre": {}}},
    }


def create_song_query(query):
    """Create the Elasticsearch query for songs."""
    return {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "name^3",
                    "lyrics^2",
                    "album_genre^2",
                    "language",
                    "summary",
                ],
                "fuzziness": "AUTO",
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "name": {},
                "lyrics": {},
                "album_genre": {},
                "summary": {},
            }
        },
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
        snippet = next(
            (
                highlight[field][0]
                for field in ["abstract", "dbp_abstract", "genres"]
                if field in highlight
            ),
            source.get("abstract", source.get("dbp_abstract", "")),
        )

        results.append(
            {
                "id": hit["_id"],
                "title": title,
                "content": (
                    f"{snippet[:200]}..." if snippet and len(snippet) > 200 else snippet
                ),
                "type": "artists",
                "score": hit["_score"],
                "source": source,
            }
        )

    # Process nested member matches
    for inner_hit in inner_hits:
        member = inner_hit["_source"]
        title = member.get("name", "Unknown Member")
        snippet = member.get("dbp_abstract", member.get("abstract", ""))
        if not snippet and member.get("nameVariations"):
            snippet = f"Also known as: {', '.join(member['nameVariations'])}"

        results.append(
            {
                "id": f"{hit['_id']}_{inner_hit['_nested']['offset']}",
                "title": title,
                "content": (
                    f"{snippet[:200]}..." if snippet and len(snippet) > 200 else snippet
                ),
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
    snippet = next(
        (highlight[field][0] for field in ["genre"] if field in highlight),
        source.get("genre", ""),
    )

    return {
        "id": hit["_id"],
        "title": title,
        "content": snippet,
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
    snippet = next(
        (
            highlight[field][0]
            for field in ["lyrics", "summary", "album_genre"]
            if field in highlight
        ),
        source.get("lyrics", source.get("summary", source.get("album_genre", ""))),
    )

    return {
        "id": hit["_id"],
        "title": title,
        "content": (
            f"{snippet[:200]}..." if snippet and len(snippet) > 200 else snippet
        ),
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

    for hit in hits:
        # Clean HTML tags from title and content
        hit["title"] = remove_html_tags(hit["title"])
        hit["content"] = remove_html_tags(hit["content"])

        # Create a key for deduplication (type + cleaned title)
        key = hit["title"].lower()

        # Only add if we haven't seen this title for this type
        if key not in seen_titles[hit["type"]]:
            seen_titles[hit["type"]].add(key)
            cleaned_hits.append(hit)

    # Sort all hits by score
    cleaned_hits.sort(key=lambda x: x["score"], reverse=True)
    return cleaned_hits
