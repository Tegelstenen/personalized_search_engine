# First, you need to setup the local elastic engine

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

# To run the web app

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

# To get the corpus

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

# To calculate the embeddings

```zsh
uv run src/embedding.py -i SONG_JSON_DIR -o OUTPUT_DIR
```

then you need to replace the original `song.json` with the output json file, and re-index to load these embeddings on Elastic Search
you can also specify the batch size with `-b BATCH_SIZE` and which field for embedding with `-f FIELD_NAME`
