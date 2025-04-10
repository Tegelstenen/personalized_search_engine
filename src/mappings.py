INDEX_MAPPINGS = {
    "artists": {
        "properties": {
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "urlWikipedia": {"type": "keyword"},
            "urlOfficialWebsite": {"type": "keyword"},
            "urlFacebook": {"type": "keyword"},
            "urlMySpace": {"type": "keyword"},
            "urlTwitter": {"type": "keyword"},
            "locationInfo": {"type": "keyword"},
            "urlWikia": {"type": "keyword"},
            "genres": {"type": "keyword"},
            "labels": {"type": "keyword"},
            "rdf": {"type": "text", "index": False},
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
                    "begin": {"type": "keyword"},
                    "end": {"type": "keyword"},
                }
            },
            "location": {
                "properties": {
                    "id_city_musicbrainz": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "city": {"type": "keyword"},
                }
            },
            "gender": {"type": "keyword"},
            "endArea": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "disambiguation": {"type": "keyword"},
                }
            },
            "id_artist_deezer": {"type": "keyword"},
            "urlDeezer": {"type": "keyword"},
            "picture": {"enabled": False},
            "deezerFans": {"type": "integer"},
            "urlWikidata": {"type": "keyword"},
            "abstract": {"type": "text"},
            "nameVariations": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "urls": {"type": "keyword"},
            "id_artist_discogs": {"type": "keyword"},
            "subject": {"type": "keyword"},
            "associatedMusicalArtist": {"type": "keyword"},
            "dbp_genre": {"type": "keyword"},
            "recordLabel": {"type": "keyword"},
            "dbp_abstract": {"type": "text"},
            "name_accent_fold": {"type": "text"},
            "nameVariations_fold": {"type": "text"},
            "members": {
                "type": "nested",
                "properties": {
                    "id_member_musicbrainz": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "instruments": {"type": "keyword"},
                    "begin": {"type": "keyword"},
                    "end": {"type": "keyword"},
                    "ended": {"type": "boolean"},
                    "disambiguation": {"type": "text"},
                    "type": {"type": "keyword"},
                    "gender": {"type": "keyword"},
                    "urlAllmusic": {"type": "keyword"},
                    "urlDiscogs": {"type": "keyword"},
                    "urlWikidata": {"type": "keyword"},
                    "urlWikipedia": {"type": "keyword"},
                    "id_member_discogs": {"type": "keyword"},
                    "realName": {"type": "text"},
                    "abstract": {"type": "text"},
                    "nameVariations": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "urls": {"type": "keyword"},
                    "urlEquipBoard": {"type": "keyword"},
                    "equipments": {"type": "object", "enabled": False},
                    "subject": {"type": "keyword"},
                    "birthDate": {
                        "type": "date",
                        "format": "yyyy||yyyy-MM-dd",
                        "ignore_malformed": True,
                    },
                    "dbp_abstract": {"type": "text"},
                },
            },
        }
    },
    "albums": {
        "properties": {
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "urlWikipedia": {"type": "keyword"},
            "genre": {"type": "keyword"},
            "length": {"type": "keyword"},
            "urlAlbum": {"type": "keyword"},
            "id_artist": {"type": "keyword"},
            "rdf": {"type": "text", "index": False},
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "publicationDate": {"type": "date", "format": "yyyy||yyyy-MM-dd"},
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
            "dateRelease": {"type": "date", "ignore_malformed": True},
            "language": {"type": "keyword"},
            "id_album_deezer": {"type": "keyword"},
            "urlDeezer": {"type": "keyword"},
            "cover": {"enabled": False},
            "deezerFans": {"type": "integer"},
            "explicitLyrics": {"type": "boolean"},
            "upc": {"type": "keyword"},
            "id_album_discogs": {"type": "keyword"},
        }
    },
    "songs": {
        "properties": {
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "position": {"type": "integer"},
            "lengthAlbum": {"type": "keyword"},
            "urlSong": {"type": "keyword"},
            "lyrics": {"type": "text", "analyzer": "english"},
            "urlWikipedia": {"type": "keyword"},
            "id_album": {"type": "keyword"},
            "isClassic": {"type": "boolean"},
            "urlAllmusic": {"type": "keyword"},
            "urlMusicBrainz": {"type": "keyword"},
            "publicationDateAlbum": {"type": "date", "format": "yyyy"},
            "albumTitle": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "id_song_deezer": {"type": "keyword"},
            "isrc": {"type": "keyword"},
            "length": {"type": "integer"},
            "explicitLyrics": {"type": "boolean"},
            "rank": {"type": "integer"},
            "bpm": {"type": "float"},
            "gain": {"type": "float"},
            "preview": {"type": "keyword"},
            "availableCountries": {"type": "keyword"},
            "publicationDate": {"type": "date", "ignore_malformed": True},
            "rdf": {"type": "text", "index": False},
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
            "id_artist_deezer": {"type": "keyword"},
            "id_album_deezer": {"type": "keyword"},
            "urlDeezer": {"type": "keyword"},
            "language_detect": {"type": "keyword"},
            "name": {"type": "keyword"},
            "title_accent_fold": {"type": "text"},
            "chords_metadata": {
                "type": "nested",
                "properties": {
                    "confidence": {"type": "float"},
                    "duration": {"type": "float"},
                    "chordSequence": {
                        "type": "nested",
                        "properties": {
                            "start": {"type": "float"},
                            "end": {"type": "float"},
                            "label": {"type": "keyword"},
                        },
                    },
                },
            },
        }
    },
    "topics": {
        "properties": {"topic_id": {"type": "keyword"}, "terms": {"type": "keyword"}}
    },
    "emotions": {
        "properties": {
            "lastfm_id": {"type": "keyword"},
            "song_id": {"type": "keyword"},
            "emotions": {
                "properties": {
                    "type": "nested",
                    "emotion_tag": {"type": "keyword"},
                    "nbr_tags": {"type": "integer"},
                }
            },
        }
    },
    "social_tags": {
        "properties": {
            "lastfm_id": {"type": "keyword"},
            "socials": {
                "type": "nested",
                "properties": {
                    "social_tag": {"type": "keyword"},
                    "nbr_tags": {"type": "integer"},
                },
            },
        }
    },
    "song_topics": {
        "properties": {
            "id_song": {"type": "keyword"},
            "topics": {
                "type": "nested",
                "properties": {
                    "topic": {"type": "keyword"},
                    "probability": {"type": "float"},
                },
            },
        }
    },
}
