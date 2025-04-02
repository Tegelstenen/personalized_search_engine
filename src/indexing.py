from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from dotenv import load_dotenv

import json
import os

from mappings import INDEX_MAPPINGS

load_dotenv()

# --- Configuration ---
CORPUS_DIR = "corpus" # Directory containing your JSON files
FILE_TO_INDEX_MAP = {
    "artist-without-members.json": "artists",
    "album.json": "albums",
    "song.json": "songs",
    "topic-models.json": "topics",
    "emotion-tags.json": "emotions",
}
BULK_CHUNK_SIZE = 500 # How many documents to send in each bulk request

# --- Helper Functions ---
def connect_es():
    """Connects to Elasticsearch"""
    print("Connecting to Elasticsearch...")
    try:
        es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", os.environ.get("ES_LOCAL_PASSWORD")) )
        es.info() # Check connection
        print("Connected to Elasticsearch successfully.")
        return es
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        exit()

def create_index(es_client, index_name, mapping):
    """Creates an Elasticsearch index if it doesn't exist"""
    if not es_client.indices.exists(index=index_name):
        print(f"Creating index '{index_name}'...")
        try:
            es_client.indices.create(index=index_name, mappings=mapping)
            print(f"Index '{index_name}' created.")
        except Exception as e:
            print(f"Error creating index '{index_name}': {e}")
    else:
        print(f"Index '{index_name}' already exists.")

def generate_bulk_actions(filepath, index_name):
    """Generator function to yield bulk actions for documents in a file"""
    print(f"Processing file: {filepath} for index: {index_name}")
    count = 0
    # Assuming one JSON object per line (JSON Lines format)
    # If the file is a single JSON array, adjust the reading logic
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    # Extract the $oid for the document ID
                    doc_id = doc.get('_id', {}).get('$oid')
                    if not doc_id:
                        print(f"Skipping document without '_id.$oid' in {filepath}")
                        continue

                    # --- Data Cleaning/Transformation ---
                    # Remove the original _id field as we use $oid for ES _id
                    if '_id' in doc:
                        del doc['_id']

                    # Handle nested $oid references (like id_artist, id_album, song_id)
                    # You might need to add specific checks per index_name if structures differ widely
                    for key, value in list(doc.items()): # Iterate over a copy of items
                         if isinstance(value, dict) and '$oid' in value:
                             doc[key] = value['$oid'] # Replace the dict with just the ID string

                    # You might need more specific date parsing/formatting here if
                    # Elasticsearch 'ignore_malformed' isn't sufficient or formats are very inconsistent.

                    # Yield the bulk action dictionary
                    yield {
                        "_index": index_name,
                        "_id": doc_id,
                        "_source": doc
                    }
                    count += 1
                except json.JSONDecodeError as json_err:
                    print(f"Skipping line due to JSON decode error in {filepath}: {json_err} - Line: {line[:100]}...") # Print start of line
                except Exception as e:
                    print(f"Skipping document due to error during processing: {e} - Doc ID (if available): {doc_id}")

    except FileNotFoundError:
        print(f"Error: File not found {filepath}")
    except Exception as e:
         print(f"Error reading file {filepath}: {e}")

    print(f"Finished processing {filepath}. Found {count} valid documents.")


# --- Main Execution ---
if __name__ == "__main__":
    es = connect_es()

    # 1. Create indices with mappings
    for index_name, mapping in INDEX_MAPPINGS.items():
        create_index(es, index_name, mapping)

    # 2. Index data from files
    print("\nStarting data indexing...")
    for filename, index_name in FILE_TO_INDEX_MAP.items():
        filepath = os.path.join(CORPUS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found, skipping: {filepath}")
            continue

        # Use the bulk helper
        try:
            success, errors = bulk(
                client=es,
                actions=generate_bulk_actions(filepath, index_name),
                chunk_size=BULK_CHUNK_SIZE,
                request_timeout=60 # Increase timeout if needed
            )
            print(f"Bulk indexing for {filename}: Success={success}, Errors={len(errors)}")
            if errors:
                print("First 5 errors:", errors[:5]) # Print details of some errors
        except Exception as e:
            print(f"Error during bulk indexing for {filepath}: {e}")

    print("\nIndexing process finished.")