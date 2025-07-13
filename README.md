# Personalized search engine for music lovers
Ever searched for "energetic workout songs" or "rainy day music" and received generic results that don't quite match your vibe? This search engine solves that problem. It gets to know you by building a dynamic musical profile based on your listening habits—what you search for, which songs you click on, and what you play.

Instead of just re-ranking a standard set of results, our engine intelligently blends your musical profile with your search query before the search even begins. This creates a unique, personalized query that reflects both your immediate intent and your long-term preferences. The result is a more relevant and satisfying music discovery experience, surfacing tracks that are not only a good match for your query but also a great match for you.

## Key Features 🎵
- Spotify Integration: Log in with your Spotify account to stream music directly through our interface.
- Dynamic User Profiles: Your profile is built from your interactions (searches, clicks, and playbacks) and evolves over time.
- Hybrid Search: We combine the power of semantic search with traditional keyword search to ensure both relevance and precision. This is all fused together using Reciprocal Rank Fusion.
- Deep Personalization: The core of our engine is the fusion of your user profile embedding with your query embedding, creating a search that is truly tailored to your tastes.
- User Analytics Dashboard: Visualize your listening habits, including your top genres, artists, and liked songs over time.

# Setup
## First, you need to setup the local elastic engine

```zsh
curl -fsSL https://elastic.co/start-local | sh

cp elastic-start-local/.env .

sh elastic-start-local/start.sh
```

### Endpoints

After running the script:

- Elasticsearch will be running at http://localhost:9200
- Kibana will be running at http://localhost:5601

### more info

- [initial setup](https://github.com/elastic/start-local?tab=readme-ov-file#-try-elasticsearch-and-kibana-locally)

- [elastic python documentation](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/overview.html)

## To run the web app

install uv if you do not have it

```zsh
brew install uv
```

use uv as package manager:

```zsh
uv venv
source .venv/bin/activate
uv add -r requirements.txt
uv run app.py
```

or simply:

```zsh
uv run app.py
```

then you can see the GUI locally on http://127.0.0.1:5000

## To get the corpus

```zsh
mkdir corpus
curl -L "https://zenodo.org/records/5603369/files/wasabi-2-0.tar?download=1" -o corpus/wasabi-2-0.tar
cd corpus
tar -xf wasabi-2-0.tar
cd json
unzip json.zip -d ../
cd ..
rm -rf json rdf wasabi-2-0.tar
cd ..
```

remove any other files in the corpus folder except for `album.json`, `artist-without-members.json`, and `song.json`

## Start indexing

```zsh
uv run src/indexing.py
```

## To calculate the embeddings

```zsh
uv run src/embedding.py -i SONG_JSON_DIR -o OUTPUT_DIR
```

then you need to replace the original `song.json` with the output json file, and re-index to load these embeddings on Elastic Search
you can also specify the batch size with `-b BATCH_SIZE` and which field for embedding with `-f FIELD_NAME`
