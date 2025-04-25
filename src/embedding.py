import argparse
import os

import ijson
import simplejson as json
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import html


def process_large_json(input_file, output_file, batch_size=1000, field="title"):
    """
    Process a large JSON file by adding title embeddings in batches.

    Args:
        input_file: Path to the input JSON file
        output_file: Path to the output JSON file
        batch_size: Number of songs to process in each batch
        :param batch_size:
        :param output_file:
        :param input_file:
        :param field:
    """
    # Initialize the embedding model
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    temp_dir = "temp_batches"
    os.makedirs(temp_dir, exist_ok=True)

    batch = []
    batch_num = 0
    batch_files = []

    with open(input_file, 'r') as f:
        items = ijson.items(f, 'item')
        pbar = tqdm(desc="Processing songs", unit="songs")

        for song in items:
            batch.append(song)

            if len(batch) >= batch_size:
                batch_file = process_batch(batch, model, temp_dir, batch_num, field)
                batch_files.append(batch_file)
                batch_num += 1
                pbar.update(len(batch))
                batch = []

        # Final batch
        if batch:
            batch_file = process_batch(batch, model, temp_dir, batch_num, field)
            batch_files.append(batch_file)
            pbar.update(len(batch))

        pbar.close()

    # Combine batches
    combine_batch_files(batch_files, output_file)

    # Cleanup
    for file in batch_files:
        os.remove(file)
    os.rmdir(temp_dir)

    print(f"\n✅ Processing complete. Output saved to: {output_file}")


def process_batch(batch, model, temp_dir, batch_num, field):
    """Add embeddings to a batch of songs."""
    if field == 'lyrics':
        # print("embedding lyrics..")
        # remove html style in dataset
        field_vals = [html.unescape(song.get(field, "")).replace("<br>", ". ") for song in batch]
        # print("field_vals: " + str(field_vals))
    else:
        field_vals = [song.get(field, "") for song in batch]

    embeddings = model.encode(field_vals, batch_size=32, show_progress_bar=False).tolist()

    embedding_field_name = field + "_embedding"

    for song, embedding in zip(batch, embeddings):
        song[embedding_field_name] = embedding

    batch_file = os.path.join(temp_dir, f"batch_{batch_num}.json")
    with open(batch_file, "w") as f:
        json.dump(batch, f)

    return batch_file


def combine_batch_files(batch_files, output_file):
    """Combine all batch files into a single output file."""
    with open(output_file, 'w') as out_f:
        out_f.write('[')

        for i, file_path in enumerate(batch_files):
            with open(file_path, 'r') as in_f:
                content = in_f.read()
                # Remove the opening and closing brackets from the batch JSON
                content = content.strip()
                if content.startswith('['):
                    content = content[1:]
                if content.endswith(']'):
                    content = content[:-1]

                out_f.write(content)

                # Add comma if not the last batch
                if i < len(batch_files) - 1:
                    out_f.write(',')

        out_f.write(']')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add title embeddings to large JSON file of songs")
    parser.add_argument("-i", "--input", required=True, help="Path to input JSON file")
    parser.add_argument("-o", "--output", required=True, help="Path to output JSON file")
    parser.add_argument("-b", "--batch-size", type=int, default=2048, help="Batch size (default: 2048)")
    parser.add_argument("-f", "--field", type=str, default="title", help="Field for embedding")

    args = parser.parse_args()
    print("field: " + args.field)
    process_large_json(args.input, args.output, batch_size=args.batch_size, field=args.field)