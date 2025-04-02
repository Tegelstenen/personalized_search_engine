#  First, you need to setup the local engine
```zsh
curl -fsSL https://elastic.co/start-local | sh

cp elastic-start-local/.env .

sh elastic-start-local/start.sh
```

## Endpoints
After running the script:

- Elasticsearch will be running at http://localhost:9200
- Kibana will be running at http://localhost:5601

## more info
- [initial setup](https://github.com/elastic/start-local?tab=readme-ov-file#-try-elasticsearch-and-kibana-locally)

- [elastic python documentation](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/overview.html)

# To run the web app
install uv if you do not have it
```zsh
brew install uv
```

use uv as package manager
```zsh
uv venv
source .venv/bin/activate
uv add -r requirements.txt
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

