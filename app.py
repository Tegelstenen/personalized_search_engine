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


# Index name to search in
INDEX_NAME = "my_documents"

# Create sample data for testing (you can replace this with your own data later)
def create_sample_data():
    # Delete index if it already exists
    if client.indices.exists(index=INDEX_NAME):
        client.indices.delete(index=INDEX_NAME)
    
    # Create index with mappings
    client.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "author": {"type": "keyword"},
                    "date": {"type": "date", "format": "yyyy-MM-dd"}
                }
            }
        }
    )
    
    # Add some sample documents
    documents = [
        {
            "title": "Introduction to Elasticsearch",
            "content": "Elasticsearch is a distributed, RESTful search and analytics engine.",
            "author": "Elastic",
            "date": "2023-01-15"
        },
        {
            "title": "Python Programming Basics",
            "content": "Python is a high-level, interpreted programming language.",
            "author": "Guido van Rossum",
            "date": "2023-02-20"
        },
        {
            "title": "Web Development with Flask",
            "content": "Flask is a lightweight WSGI web application framework in Python.",
            "author": "Armin Ronacher",
            "date": "2023-03-10"
        },
        {
            "title": "Data Analysis with Python",
            "content": "Python is widely used for data analysis with libraries like Pandas and NumPy.",
            "author": "Data Scientist",
            "date": "2023-04-05"
        },
        {
            "title": "Elasticsearch Query DSL",
            "content": "The Query DSL is a JSON-based query language for Elasticsearch.",
            "author": "Elastic",
            "date": "2023-05-22"
        }
    ]
    
    # Bulk index the documents
    for i, doc in enumerate(documents):
        client.index(index=INDEX_NAME, id=i+1, document=doc)
    
    # Refresh the index to make the documents available for search
    client.indices.refresh(index=INDEX_NAME)
    
    print(f"Created {len(documents)} sample documents in index '{INDEX_NAME}'")

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
    
    # Perform search in Elasticsearch
    search_results = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content", "author"],  # ^2 boosts the title field
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "content": {}
                }
            }
        }
    )
    
    # Format the search results
    hits = []
    for hit in search_results['hits']['hits']:
        source = hit['_source']
        highlight = hit.get('highlight', {})
        
        hits.append({
            "id": hit['_id'],
            "title": highlight.get('title', [source['title']])[0],
            "content": highlight.get('content', [source['content']])[0],
            "author": source['author'],
            "date": source['date'],
            "score": hit['_score']
        })
    
    return jsonify({"hits": hits})

if __name__ == '__main__':
    # Create sample data when the app starts
    create_sample_data()
    
    # Run the Flask app
    app.run(debug=True)