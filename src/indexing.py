import argparse
import os
import time

import ijson
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

load_dotenv()

# --- Configuration ---
CORPUS_DIR = "corpus"
FILE_TO_INDEX_MAP = {
    "artist-without-members.json": "artists",
    "album.json": "albums",
    "song.json": "songs",
}
BULK_CHUNK_SIZE = 500

# Define mappings for indices that need specific field types
SONGS_MAPPING = {
    "properties": {
        # Text fields for better search
        "title": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "title_embedding": {
            "type": "dense_vector",
            "dims": 384,
            "index": True,
            "similarity": "cosine"
        },
        "artist": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "lyrics": {
            "type": "text",
            "analyzer": "standard"
        },
        "albumTitle": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "album_genre": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "summary": {
            "type": "text",
            "analyzer": "standard"
        },
        "language": {
            "type": "keyword"
        },
        # Nested and special fields
        "deezer_mapping": {
            "type": "nested",
            "properties": {
                "0": {"type": "long", "coerce": True},
                "1": {"type": "keyword"}
            }
        },
        "chords_metadata": {
            "properties": {
                "confidence": {"type": "float", "coerce": True},
                "duration": {"type": "float", "coerce": True},
                "chordSequence": {
                    "type": "nested",
                    "properties": {
                        "start": {"type": "float", "coerce": True},
                        "end": {"type": "float", "coerce": True},
                        "label": {"type": "keyword"}
                    }
                }
            }
        },
        "publicationDate": {
            "type": "date",
            "format": "strict_date_optional_time||epoch_millis||yyyy-MM-dd||strict_date||basic_date",
            "ignore_malformed": True,
            "null_value": None
        },
        "id_album": {"type": "keyword"},
        "id_artist": {"type": "keyword"},
        "id_song_musicbrainz": {"type": "keyword"},
        "id_song_deezer": {"type": "keyword"}
    },
    "dynamic_templates": [
        {
            "strings_as_keywords": {
                "match_mapping_type": "string",
                "mapping": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        }
    ]
}

ALBUMS_MAPPING = {
    "properties": {
        # Text fields for better search
        "title": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "name": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "artist_name": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "genre": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        # ID and date fields
        "id_artist": {"type": "keyword"},
        "id_album_deezer": {"type": "keyword"},
        "id_album_musicbrainz": {"type": "keyword"},
        "id_album_discogs": {"type": "keyword"},
        "country": {"type": "keyword"},
        "language": {"type": "keyword"},
        "dateRelease": {
            "type": "date",
            "format": "strict_date_optional_time||epoch_millis||yyyy-MM-dd||strict_date||basic_date",
            "ignore_malformed": True,
            "null_value": None
        }
    },
    "dynamic_templates": [
        {
            "strings_as_keywords": {
                "match_mapping_type": "string",
                "mapping": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        }
    ]
}

ARTISTS_MAPPING = {
    "properties": {
        # Text fields for better search
        "name": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "nameVariations": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "abstract": {
            "type": "text",
            "analyzer": "standard"
        },
        "dbp_abstract": {
            "type": "text",
            "analyzer": "standard"
        },
        "genres": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "dbp_genre": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "type": {"type": "keyword"},
        "location": {
            "properties": {
                "city": {"type": "keyword"},
                "country": {"type": "keyword"}
            }
        }
    },
    "dynamic_templates": [
        {
            "strings_as_keywords": {
                "match_mapping_type": "string",
                "mapping": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        }
    ]
}

INDEX_MAPPINGS = {
    "songs": SONGS_MAPPING,
    "albums": ALBUMS_MAPPING,
    "artists": ARTISTS_MAPPING
}


# --- Helper Functions ---
def connect_es():
    print("Connecting to Elasticsearch...")
    try:
        es = Elasticsearch(
            "http://localhost:9200",
            basic_auth=("elastic", os.environ.get("ES_LOCAL_PASSWORD")),
        )
        es.info()  # Check connection
        print("Connected to Elasticsearch successfully.")
        return es
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        exit()


def create_index(es_client, index_name, mapping=None):
    if not es_client.indices.exists(index=index_name):
        print(f"Creating index '{index_name}'...")
        try:
            # Use provided mapping if available, otherwise use a basic mapping
            if mapping:
                es_client.indices.create(index=index_name, mappings=mapping)
                print(f"Created index '{index_name}' with defined mapping.")
            else:
                # Create a simple dynamic mapping for indices without a predefined structure
                es_client.indices.create(index=index_name)
                print(f"Created index '{index_name}' with dynamic mapping.")
        except Exception as e:
            print(f"Error creating index '{index_name}': {e}")
    else:
        print(f"Index '{index_name}' already exists.")


def extract_oid(value):
    """Extract the $oid value from a MongoDB-style ID object."""
    if isinstance(value, dict) and "$oid" in value:
        return value["$oid"]
    return value


def process_document(doc):
    """Process a document before indexing."""
    # Handle MongoDB-style IDs
    if "id_artist" in doc:
        doc["id_artist"] = extract_oid(doc["id_artist"])
    if "id_album" in doc:
        doc["id_album"] = extract_oid(doc["id_album"])

    # Handle deezer_mapping array structure
    if "deezer_mapping" in doc:
        if doc["deezer_mapping"] is None:
            doc["deezer_mapping"] = []
        else:
            doc["deezer_mapping"] = [
                {"0": mapping[0], "1": mapping[1]}
                for mapping in doc["deezer_mapping"]
                if isinstance(mapping, (list, tuple)) and len(mapping) == 2
            ]

    return doc


def generate_bulk_actions(filepath, index_name, subset_size=None):
    print(f"\nProcessing file: {filepath} for index: {index_name}")
    count = 0

    # Print size
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # Size in MB
    print(f"File size: {file_size:.2f} MB")

    try:
        with open(filepath, encoding="utf-8") as f:
            try:
                print("Processing JSON array using ijson streaming parser...")
                objects = ijson.items(f, 'item')
                for doc in objects:
                    try:
                        # Extract the $oid for the document ID
                        doc_id = doc.get("_id", {}).get("$oid")
                        del doc["_id"]

                        # Process MongoDB-style IDs
                        doc = process_document(doc)

                        # Yield the bulk action dictionary
                        yield {
                            "_index": index_name,
                            "_id": doc_id,
                            "_source": doc,
                        }
                        count += 1

                        # Check if we've reached subset limit
                        if subset_size and count >= subset_size:
                            print(f"Reached subset limit of {subset_size} documents")
                            break

                    except Exception as e:
                        print(f"Error processing document: {e}")

            except StopIteration:
                print("Empty file or invalid JSON format")
            except ijson.JSONError as e:
                print(f"Error parsing JSON: {e}")

    except FileNotFoundError:
        print(f"Error: File not found {filepath}")
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")

    print(f"Finished processing {filepath}. Found {count} valid documents.")


# --- Main Execution ---
if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Index data into Elasticsearch")
    parser.add_argument(
        "--subset",
        type=int,
        help="Number of documents to index per file (for debugging)",
    )
    parser.add_argument(
        "--file", type=str, help='Only process a specific file (e.g., "song.json")'
    )
    parser.add_argument(
        "--recreate-indices", action="store_true", help="Delete and recreate indices"
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="Skip files with an existing index"
    )
    args = parser.parse_args()

    # Connect to Elasticsearch
    es = connect_es()

    # Determine which files to process
    files_to_process = {}
    if args.file:
        if args.file in FILE_TO_INDEX_MAP:
            files_to_process[args.file] = FILE_TO_INDEX_MAP[args.file]
        else:
            print(
                f"Warning: Specified file '{args.file}' not found in configuration. Available files: {list(FILE_TO_INDEX_MAP.keys())}"
            )
            exit()
    else:
        files_to_process = FILE_TO_INDEX_MAP

    # Create mappings for indices
    indices_to_create = set(files_to_process.values())

    # Delete and recreate indices if requested
    if args.recreate_indices:
        for index_name in indices_to_create:
            if es.indices.exists(index=index_name):
                print(f"Deleting existing index '{index_name}'...")
                es.indices.delete(index=index_name)
                print(f"Index '{index_name}' deleted.")

    for index_name in indices_to_create:
        create_index(es, index_name, INDEX_MAPPINGS.get(index_name))

    # Index data from files
    print("\nStarting data indexing...")
    for filename, index_name in files_to_process.items():
        filepath = os.path.join(CORPUS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found, skipping: {filepath}")
            continue

        # Skip files if the index already has data and --skip-existing is set
        if args.skip_existing and es.indices.exists(index=index_name):
            # Check if index has documents (count > 0)
            count_response = es.count(index=index_name)
            if count_response["count"] > 0:
                print(
                    f"Skipping {filename} because index '{index_name}' already has {count_response['count']} documents."
                )
                continue

        # Use the bulk helper with more detailed error handling
        start_time = time.time()
        try:
            success, errors = bulk(
                client=es,
                actions=generate_bulk_actions(filepath, index_name, args.subset),
                chunk_size=BULK_CHUNK_SIZE,
                raise_on_error=False,  # Don't stop on first error
                stats_only=False,  # Get detailed error info
                request_timeout=120,  # Increase timeout for large datasets
            )

            elapsed = time.time() - start_time

            if errors:
                print(
                    f"Bulk indexing for {filename}: Success={success}, Errors={len(errors)}"
                )
                print(f"Indexing speed: {success / elapsed:.2f} docs/sec")
                print("First 5 error details:")
                for i, error in enumerate(errors[:5]):
                    print(f"Error {i + 1}:")
                    print(
                        f"  Operation: {error.get('index', {}).get('_op_type', 'unknown')}"
                    )
                    print(
                        f"  Document ID: {error.get('index', {}).get('_id', 'unknown')}"
                    )
                    print(
                        f"  Error type: {error.get('index', {}).get('error', {}).get('type', 'unknown')}"
                    )
                    print(
                        f"  Error reason: {error.get('index', {}).get('error', {}).get('reason', 'unknown')}"
                    )
            else:
                print(
                    f"Bulk indexing for {filename}: Successfully indexed {success} documents with no errors."
                )
                print(f"Indexing speed: {success / elapsed:.2f} docs/sec")

        except Exception as e:
            print(f"Error during bulk indexing for {filepath}: {e}")

    print("\nIndexing process finished.")
