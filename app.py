# app.py
from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

import os


load_dotenv()

app = Flask(__name__)

# Connect to Elasticsearch
# For local development
client = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", os.environ.get("ES_LOCAL_PASSWORD")) 
    )

# Indices to search in (from indexing.py)
MUSIC_INDICES = ["artists", "albums", "songs", "topics", "emotions"]

# Route for the home page with search form
@app.route('/')
def home():
    return render_template('index.html')

# Route for search results
@app.route('/search')
def search():
    # Get the search query from the request parameters
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({"hits": []})
    
    # Perform search in Elasticsearch across all music indices
    search_results = client.search(
        index=",".join(MUSIC_INDICES),
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "title^3", "genre^2", "description", "lyrics", "artist_name", "album_name"],
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "name": {},
                    "title": {},
                    "genre": {},
                    "description": {},
                    "lyrics": {},
                    "artist_name": {},
                    "album_name": {}
                }
            }
        }
    )
    
    # Format the search results
    hits = []
    for hit in search_results['hits']['hits']:
        source = hit['_source']
        highlight = hit.get('highlight', {})
        
        # Determine document type based on _index
        doc_type = hit['_index']
        
        # Extract the main title field based on document type
        title_field = "name" if doc_type in ["artists", "topics", "emotions"] else "title"
        title = highlight.get(title_field, [source.get(title_field, "Unknown")])[0]
        
        # Create a snippet from available highlighted content
        snippet = ""
        for field in ["description", "lyrics", "genre"]:
            if field in highlight:
                snippet = highlight[field][0]
                break
        
        # If no highlighted snippet was found, use a field from source
        if not snippet:
            for field in ["description", "lyrics", "genre"]:
                if field in source:
                    snippet = source[field]
                    # Truncate long text
                    if isinstance(snippet, str) and len(snippet) > 200:
                        snippet = snippet[:200] + "..."
                    break
        
        # Create a result object with common fields
        result = {
            "id": hit['_id'],
            "title": title,
            "content": snippet,
            "type": doc_type,
            "score": hit['_score'],
            # Add all source fields for type-specific rendering
            "source": source
        }
        
        hits.append(result)
    
    return jsonify({"hits": hits})

if __name__ == '__main__':
    # No need to create sample data, it's already indexed by indexing.py
    
    # Run the Flask app
    app.run(debug=True)