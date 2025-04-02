INDEX_MAPPINGS = {
    "artists": {
        "properties": {
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "urlWikipedia": {"type": "keyword"},
            "urlOfficialWebsite": {"type": "keyword"},
            "urlFacebook": {"type": "keyword"},
            "urlMySpace": {"type": "keyword"},
            "urlTwitter": {"type": "keyword"},
            "locationInfo": {"type": "keyword"}, # For filtering/aggregation by location parts
            "urlWikia": {"type": "keyword"},
            "genres": {"type": "keyword"}, # Assuming you want to filter/aggregate by genre
            "labels": {"type": "keyword"},
            "rdf": {"type": "text", "index": False}, # Indexing RDF as text might be limited. Consider parsing or disabling indexing if not needed for search.
            "urlAmazon": {"type": "keyword"},
            "urlITunes": {"type": "keyword"},
            "urlAllmusic": {"type": "keyword"},
            "urlDiscogs": {"type": "keyword"},
            "urlMusicBrainz": {"type": "keyword"},
            "urlYouTube": {"type": "keyword"},
            "urlSpotify": {"type": "keyword"},
            "urlPureVolume": {"type": "keyword"},
            "urlRateYourMusic": {"type": "keyword"},
            "urlSoundCloud": {"type": "keyword"},
            "id_artist_musicbrainz": {"type": "keyword"},
            "disambiguation": {"type": "text"},
            "type": {"type": "keyword"},
            "lifeSpan": {
                "properties": {
                    "ended": {"type": "boolean"},
                    "begin": {"type": "keyword"}, # Or date if format is consistent
                    "end": {"type": "keyword"}    # Or date
                }
            },
            "location": {
                 "properties": {
                    "id_city_musicbrainz": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "city": {"type": "keyword"}
                }
            },
            "gender": {"type": "keyword"},
             "endArea": {
                 "properties": {
                     "id": {"type": "keyword"},
                     "name": {"type": "keyword"},
                     "disambiguation": {"type": "keyword"}
                 }
             },
            "id_artist_deezer": {"type": "keyword"},
            "urlDeezer": {"type": "keyword"},
            "picture": { # Not indexing picture URLs by default, adjust if needed
                "enabled": False
            },
            "deezerFans": {"type": "integer"},
            "urlWikidata": {"type": "keyword"},
            "abstract": {"type": "text"},
            "nameVariations": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "urls": {"type": "keyword"},
            "id_artist_discogs": {"type": "keyword"},
            "subject": {"type": "keyword"}, # Good for filtering/faceting
            "associatedMusicalArtist": {"type": "keyword"}, # Assuming IDs or names
            "dbp_genre": {"type": "keyword"},
            "recordLabel": {"type": "keyword"},
            "dbp_abstract": {"type": "text"},
            "name_accent_fold": {"type": "text"},
            "nameVariations_fold": {"type": "text"}
        }
    },
    "albums": {
        "properties": {
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "urlWikipedia": {"type": "keyword"},
            "genre": {"type": "keyword"},
            "length": {"type": "keyword"}, # Could be tricky to query ranges, maybe store seconds as integer?
            "urlAlbum": {"type": "keyword"},
            "id_artist": {"type": "keyword"}, # Reference to the artist document ID
            "rdf": {"type": "text", "index": False},
            "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "publicationDate": {"type": "date", "formats": ["yyyy", "yyyy-MM-dd||yyyy"]}, # Handle year-only format
            "urlAmazon": {"type": "keyword"},
            "urlITunes": {"type": "keyword"},
            "urlAllmusic": {"type": "keyword"},
            "urlDiscogs": {"type": "keyword"},
            "urlMusicBrainz": {"type": "keyword"},
            "urlSpotify": {"type": "keyword"},
            "id_album_musicbrainz": {"type": "keyword"},
            "country": {"type": "keyword"},
            "disambiguation": {"type": "text"},
            "barcode": {"type": "keyword"},
            "dateRelease": {"type": "date", "ignore_malformed": True}, # Handle potential formatting issues
            "language": {"type": "keyword"},
            "id_album_deezer": {"type": "keyword"},
            "urlDeezer": {"type": "keyword"},
            "cover": {"enabled": False},
            "deezerFans": {"type": "integer"},
            "explicitLyrics": {"type": "boolean"},
            "upc": {"type": "keyword"},
            "id_album_discogs": {"type": "keyword"}
            # Add other fields as needed
        }
    },
    "songs": {
        "properties": {
            "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "position": {"type": "integer"},
            "lengthAlbum": {"type": "keyword"},
            "urlSong": {"type": "keyword"},
            "lyrics": {"type": "text", "analyzer": "english"}, # Use appropriate analyzer for lyrics search
            "urlWikipedia": {"type": "keyword"},
            "id_album": {"type": "keyword"}, # Reference to the album document ID
            "isClassic": {"type": "boolean"},
            "urlAllmusic": {"type": "keyword"},
            "urlMusicBrainz": {"type": "keyword"},
            "publicationDateAlbum": {"type": "date", "formats": ["yyyy"]},
            "albumTitle": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            "id_song_deezer": {"type": "keyword"},
            "isrc": {"type": "keyword"},
            "length": {"type": "integer"}, # Assuming this is seconds
            "explicitLyrics": {"type": "boolean"},
            "rank": {"type": "integer"},
            "bpm": {"type": "float"}, # Beats per minute
            "gain": {"type": "float"},
            "preview": {"type": "keyword"},
            "availableCountries": {"type": "keyword"},
            "publicationDate": {"type": "date", "ignore_malformed": True},
             "rdf": {"type": "text", "index": False}, # If rdf field exists
             "urlPandora": {"type": "keyword"},
             "urlITunes": {"type": "keyword"},
             "urlSpotify": {"type": "keyword"},
             "urlYouTube": {"type": "keyword"},
             "urlAmazon": {"type": "keyword"},
             "urlHypeMachine": {"type": "keyword"},
             "urlGoEar": {"type": "keyword"},
             "urlLastFm": {"type": "keyword"},
             "id_song_musicbrainz": {"type": "keyword"},
             "language": {"type": "keyword"},
             "id_artist_deezer": {"type": "keyword"}, # Reference to artist
             "id_album_deezer": {"type": "keyword"}, # Reference to album
             "urlDeezer": {"type": "keyword"},
             "language_detect": {"type": "keyword"},
             "name": {"type": "keyword"}, # Song name again? Or Artist name? Clarify. Assume Artist Name here.
             "title_accent_fold": {"type": "text"},
            "chords_metadata": { # Use nested type for chords
                "type": "nested",
                "properties": {
                    "confidence": {"type": "float"},
                    "duration": {"type": "float"},
                    "chordSequence": {
                         "type": "nested", # Nested again for sequence items
                         "properties": {
                             "start": {"type": "float"},
                             "end": {"type": "float"},
                             "label": {"type": "keyword"} # Chord label
                         }
                    }
                }
            }
            # Add other fields as needed
        }
    },
    "topics": {
        "properties": {
            "topic_id": {"type": "keyword"},
            "terms": {"type": "keyword"} # Or text if you want to search within terms
        }
    },
    "emotions": {
         "properties": {
             "lastfm_id": {"type": "keyword"},
             "song_id": {"type": "keyword"}, # Reference to the song document ID
             "emotions": {
                 "type": "nested", # Use nested type for list of emotion objects
                 "properties": {
                    "emotion_tag": {"type": "keyword"},
                    "nbr_tags": {"type": "integer"}
                 }
            }
         }
    }
}