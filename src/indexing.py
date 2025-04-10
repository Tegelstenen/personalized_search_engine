import argparse
import json
import os
import re
import time

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from mappings import INDEX_MAPPINGS

load_dotenv()

# --- Configuration ---
CORPUS_DIR = "corpus"
FILE_TO_INDEX_MAP = {
    "artist-without-members.json": "artists",
    "artist-members.json": "artists",
    "album.json": "albums",
    "song.json": "songs",
    "topic-models.json": "topics",
    "emotion-tags.json": "emotions",
    "social-tags.json": "social_tags",
    "song-topic.json": "song_topics",
}
BULK_CHUNK_SIZE = 500
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB threshold for determining large files


# --- Helper Functions ---
def connect_es():
    """Connects to Elasticsearch"""
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
    """Creates an Elasticsearch index if it doesn't exist"""
    if not es_client.indices.exists(index=index_name):
        print(f"Creating index '{index_name}'...")
        try:
            # Use provided mapping if available, otherwise use a basic mapping
            if mapping:
                es_client.indices.create(index=index_name, mappings=mapping)
            else:
                # Create a simple dynamic mapping for indices without a predefined structure
                es_client.indices.create(index=index_name)
                print(f"Created index '{index_name}' with dynamic mapping.")
            print(f"Index '{index_name}' created.")
        except Exception as e:
            print(f"Error creating index '{index_name}': {e}")
    else:
        print(f"Index '{index_name}' already exists.")


def is_large_file(filepath, threshold=LARGE_FILE_THRESHOLD):
    """Check if a file is large based on its size"""
    return os.path.getsize(filepath) > threshold


def generate_bulk_actions(filepath, index_name, subset_size=None):
    """Generator function to yield bulk actions for documents in a file"""
    print(f"Processing file: {filepath} for index: {index_name}")
    count = 0
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # Size in MB
    print(f"File size: {file_size:.2f} MB")

    try:
        # If the file is large, use line-by-line processing
        if is_large_file(filepath):
            print(f"Using line-by-line processing for large file")
            with open(filepath, encoding="utf-8") as f:
                # Check if the file starts with a JSON array bracket
                first_char = f.read(1)
                f.seek(0)  # Reset file pointer to the beginning

                if first_char == "[":
                    print("File is a JSON array. Using iterative JSON parser...")
                    # Skip the initial '[' character
                    f.read(1)

                    # Initialize for JSON object parsing
                    brackets_depth = 0
                    in_string = False
                    escape_next = False
                    current_object = ""

                    # Process subset limits
                    if subset_size:
                        print(f"Using subset of {subset_size} documents for debugging")

                    # For tracking progress
                    last_progress_time = time.time()
                    start_time = last_progress_time

                    # Process character by character
                    char = f.read(1)
                    while char:
                        current_object += char

                        # Handle string escape sequences
                        if in_string:
                            if char == "\\":
                                escape_next = not escape_next
                            elif char == '"' and not escape_next:
                                in_string = False
                            else:
                                escape_next = False
                        else:
                            if char == '"':
                                in_string = True
                            elif char == "{":
                                brackets_depth += 1
                            elif char == "}":
                                brackets_depth -= 1
                                if brackets_depth == 0:
                                    # We've completed an object
                                    try:
                                        # Parse and process the object
                                        doc = json.loads(current_object)

                                        # Extract the $oid for the document ID
                                        doc_id = doc.get("_id", {}).get("$oid")
                                        if not doc_id:
                                            print(
                                                f"Skipping document without '_id.$oid'"
                                            )
                                        else:
                                            # Process the document (cleaning, transformations, etc.)
                                            processed_doc = process_document(
                                                doc, index_name
                                            )

                                            # Yield the bulk action dictionary
                                            if processed_doc:
                                                yield {
                                                    "_index": index_name,
                                                    "_id": doc_id,
                                                    "_source": processed_doc,
                                                }
                                                count += 1

                                                # Check if we've reached subset limit
                                                if subset_size and count >= subset_size:
                                                    print(
                                                        f"Reached subset limit of {subset_size} documents"
                                                    )
                                                    break
                                    except json.JSONDecodeError as e:
                                        print(f"Error parsing JSON object: {e}")

                                    # Skip comma and whitespace to get to the next object
                                    current_object = ""
                                    next_char = f.read(1)
                                    while (
                                        next_char
                                        and next_char.isspace()
                                        or next_char == ","
                                    ):
                                        next_char = f.read(1)

                                    # Put back the first character of the next object if it's not empty
                                    if next_char:
                                        f.seek(f.tell() - 1)

                            # Show progress every 30 seconds
                            current_time = time.time()
                            if current_time - last_progress_time > 30:
                                elapsed = current_time - start_time
                                print(
                                    f"Processed {count} documents in {elapsed:.2f} seconds ({count/elapsed:.2f} docs/sec)"
                                )
                                last_progress_time = current_time

                        char = f.read(1)
                else:
                    # Process as JSONL (one JSON object per line)
                    print("Processing as JSONL (one JSON object per line)")

                    # For subset processing
                    subset_counter = 0
                    last_progress_time = time.time()
                    start_time = last_progress_time

                    for line in f:
                        # Check subset limit
                        if subset_size and subset_counter >= subset_size:
                            break

                        line = line.strip()
                        if not line:
                            continue

                        try:
                            doc = json.loads(line)
                            # Extract the $oid for the document ID
                            doc_id = doc.get("_id", {}).get("$oid")
                            if not doc_id:
                                print(f"Skipping document without '_id.$oid'")
                                continue

                            # Process the document
                            processed_doc = process_document(doc, index_name)

                            # Yield the bulk action dictionary if processing was successful
                            if processed_doc:
                                yield {
                                    "_index": index_name,
                                    "_id": doc_id,
                                    "_source": processed_doc,
                                }
                                count += 1
                                subset_counter += 1

                                # Show progress periodically
                                current_time = time.time()
                                if current_time - last_progress_time > 30:
                                    elapsed = current_time - start_time
                                    print(
                                        f"Processed {count} documents in {elapsed:.2f} seconds ({count/elapsed:.2f} docs/sec)"
                                    )
                                    last_progress_time = current_time
                        except json.JSONDecodeError as json_err:
                            print(
                                f"Skipping line due to JSON decode error: {json_err} - Line: {line[:100]}..."
                            )  # Print start of line
                        except Exception as e:
                            print(f"Skipping document due to error: {e}")
        else:
            # For smaller files, load the entire file into memory
            print("Processing smaller file in memory")
            with open(filepath, encoding="utf-8") as f:
                # Try to parse the file as a JSON array
                try:
                    documents = json.load(f)
                    # If successful, process each document in the array
                    if isinstance(documents, list):
                        print(f"Processing JSON array with {len(documents)} items")

                        # Apply subsetting if specified
                        if subset_size and subset_size < len(documents):
                            print(
                                f"Using subset of {subset_size} documents for debugging"
                            )
                            documents = documents[:subset_size]

                        for doc in documents:
                            try:
                                # Extract the $oid for the document ID
                                doc_id = doc.get("_id", {}).get("$oid")
                                if not doc_id:
                                    print(f"Skipping document without '_id.$oid'")
                                    continue

                                # Process the document
                                processed_doc = process_document(doc, index_name)

                                # Yield the bulk action dictionary if processing was successful
                                if processed_doc:
                                    yield {
                                        "_index": index_name,
                                        "_id": doc_id,
                                        "_source": processed_doc,
                                    }
                                    count += 1
                            except Exception as e:
                                print(f"Error processing document: {e}")
                    else:
                        print(f"Warning: {filepath} is not a JSON array")

                # If the file is not a JSON array, try processing it as JSONL
                except json.JSONDecodeError:
                    print(f"Not a valid JSON array, trying as JSONL")
                    # Reset file pointer to the beginning
                    f.seek(0)

                    # For subsetting
                    subset_counter = 0

                    for line in f:
                        # Check subset limit
                        if subset_size and subset_counter >= subset_size:
                            break

                        line = line.strip()
                        if not line:
                            continue

                        try:
                            doc = json.loads(line)
                            # Extract the $oid for the document ID
                            doc_id = doc.get("_id", {}).get("$oid")
                            if not doc_id:
                                print(f"Skipping document without '_id.$oid'")
                                continue

                            # Process the document
                            processed_doc = process_document(doc, index_name)

                            # Yield the bulk action dictionary if processing was successful
                            if processed_doc:
                                yield {
                                    "_index": index_name,
                                    "_id": doc_id,
                                    "_source": processed_doc,
                                }
                                count += 1
                                subset_counter += 1
                        except json.JSONDecodeError as json_err:
                            print(f"Skipping line due to JSON decode error: {json_err}")
                        except Exception as e:
                            print(f"Error processing document: {e}")

    except FileNotFoundError:
        print(f"Error: File not found {filepath}")
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")

    print(f"Finished processing {filepath}. Found {count} valid documents.")


def process_document(doc, index_name, filename=""):
    """Process a document with cleaning and transformations"""
    try:
        # Create a copy of the document to avoid modifying the original
        processed_doc = doc.copy()

        # Remove the original _id field as we use $oid for ES _id
        if "_id" in processed_doc:
            del processed_doc["_id"]

        # Handle nested $oid references (like id_artist, id_album, song_id)
        for key, value in list(processed_doc.items()):  # Iterate over a copy of items
            if isinstance(value, dict) and "$oid" in value:
                processed_doc[key] = value[
                    "$oid"
                ]  # Replace the dict with just the ID string

        # Special handling for artist-members.json
        if (
            filename == "artist-members.json"
            or os.path.basename(filename) == "artist-members.json"
        ):
            # Handle the members array
            if "members" in processed_doc and isinstance(
                processed_doc["members"], list
            ):
                for member in processed_doc["members"]:
                    # No special processing needed for equipments anymore - we're disabling indexing entirely
                    # Just leave it as is - Elasticsearch will store but not index the object

                    # Fix the birthDate format
                    if "birthDate" in member:
                        if not member["birthDate"]:
                            del member["birthDate"]
                        elif isinstance(member["birthDate"], str) and re.match(
                            r"^\d{4}$", member["birthDate"]
                        ):
                            # Keep as is - the mapping will handle years correctly
                            pass

        # Index-specific processing
        if index_name == "albums":
            # Handle cover field
            if "cover" in processed_doc:
                del processed_doc["cover"]

            # Handle problematic publication dates
            if "publicationDate" in processed_doc:
                # Handle empty values
                if not processed_doc["publicationDate"]:
                    del processed_doc["publicationDate"]
                elif isinstance(processed_doc["publicationDate"], str):
                    # Enhanced pattern matching for complex date strings:
                    # First look for a simple year pattern at beginning
                    year_match = re.match(
                        r"^(\d{4})(?:\)|\?|$)", processed_doc["publicationDate"]
                    )

                    if year_match:
                        processed_doc["publicationDate"] = year_match.group(1)
                    else:
                        # Try more aggressive pattern matching - find the first 4 digit sequence
                        year_match = re.search(
                            r"(\d{4})", processed_doc["publicationDate"]
                        )
                        if year_match:
                            processed_doc["publicationDate"] = year_match.group(1)
                        else:
                            # If no valid year found, remove the field
                            del processed_doc["publicationDate"]

            # Handle dateRelease with the same approach
            if "dateRelease" in processed_doc:
                if not processed_doc["dateRelease"]:
                    del processed_doc["dateRelease"]
                elif isinstance(processed_doc["dateRelease"], str):
                    # First try standard date format YYYY-MM-DD
                    date_match = re.match(
                        r"^(\d{4}-\d{2}-\d{2})", processed_doc["dateRelease"]
                    )
                    if date_match:
                        processed_doc["dateRelease"] = date_match.group(1)
                    else:
                        # Then try to extract just a year
                        year_match = re.search(r"(\d{4})", processed_doc["dateRelease"])
                        if year_match:
                            processed_doc["dateRelease"] = year_match.group(1)
                        else:
                            # If no valid date components found, remove the field
                            del processed_doc["dateRelease"]

        elif index_name == "songs":
            # Remove problematic deezer_mapping field
            if "deezer_mapping" in processed_doc:
                del processed_doc["deezer_mapping"]

            # Handle problematic publication dates with the same enhanced patterns
            if "publicationDateAlbum" in processed_doc:
                if not processed_doc["publicationDateAlbum"]:
                    del processed_doc["publicationDateAlbum"]
                elif isinstance(processed_doc["publicationDateAlbum"], str):
                    year_match = re.search(
                        r"(\d{4})", processed_doc["publicationDateAlbum"]
                    )
                    if year_match:
                        processed_doc["publicationDateAlbum"] = year_match.group(1)
                    else:
                        del processed_doc["publicationDateAlbum"]

            if "publicationDate" in processed_doc:
                if not processed_doc["publicationDate"]:
                    del processed_doc["publicationDate"]
                elif isinstance(processed_doc["publicationDate"], str):
                    date_match = re.match(
                        r"^(\d{4}-\d{2}-\d{2})", processed_doc["publicationDate"]
                    )
                    if date_match:
                        processed_doc["publicationDate"] = date_match.group(1)
                    else:
                        year_match = re.search(
                            r"(\d{4})", processed_doc["publicationDate"]
                        )
                        if year_match:
                            processed_doc["publicationDate"] = year_match.group(1)
                        else:
                            del processed_doc["publicationDate"]

        return processed_doc
    except Exception as e:
        print(f"Error in process_document: {e}")
        return None


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

    # Create indices with mappings
    for index_name in indices_to_create:
        # Check if we have a predefined mapping for this index
        if index_name in INDEX_MAPPINGS:
            create_index(es, index_name, INDEX_MAPPINGS[index_name])
        else:
            # For indices without predefined mappings, create with dynamic mapping
            create_index(es, index_name)

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
                print(f"Indexing speed: {success/elapsed:.2f} docs/sec")
                print("First 5 error details:")
                for i, error in enumerate(errors[:5]):
                    print(f"Error {i+1}:")
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
                print(f"Indexing speed: {success/elapsed:.2f} docs/sec")

        except Exception as e:
            print(f"Error during bulk indexing for {filepath}: {e}")

    print("\nIndexing process finished.")
