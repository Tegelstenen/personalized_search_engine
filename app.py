# app.py
import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, login_required, login_user, logout_user

from models import User, db

load_dotenv()

ES_LOCAL_PASSWORD = os.environ.get("ES_LOCAL_PASSWORD")
assert ES_LOCAL_PASSWORD is not None

app = Flask(__name__)

# Connect to Elasticsearch
# For local development
client = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", ES_LOCAL_PASSWORD),
)

# Index name to search in
INDEX_NAME = "my_documents"

# Initialize database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
                    "date": {"type": "date", "format": "yyyy-MM-dd"},
                }
            }
        },
    )

    # Add some sample documents
    documents = [
        {
            "title": "Introduction to Elasticsearch",
            "content": "Elasticsearch is a distributed, RESTful search and analytics engine.",
            "author": "Elastic",
            "date": "2023-01-15",
        },
        {
            "title": "Python Programming Basics",
            "content": "Python is a high-level, interpreted programming language.",
            "author": "Guido van Rossum",
            "date": "2023-02-20",
        },
        {
            "title": "Web Development with Flask",
            "content": "Flask is a lightweight WSGI web application framework in Python.",
            "author": "Armin Ronacher",
            "date": "2023-03-10",
        },
        {
            "title": "Data Analysis with Python",
            "content": "Python is widely used for data analysis with libraries like Pandas and NumPy.",
            "author": "Data Scientist",
            "date": "2023-04-05",
        },
        {
            "title": "Elasticsearch Query DSL",
            "content": "The Query DSL is a JSON-based query language for Elasticsearch.",
            "author": "Elastic",
            "date": "2023-05-22",
        },
    ]

    # Bulk index the documents
    for i, doc in enumerate(documents):
        client.index(index=INDEX_NAME, id=str(i + 1), document=doc)

    # Refresh the index to make the documents available for search
    client.indices.refresh(index=INDEX_NAME)

    print(f"Created {len(documents)} sample documents in index '{INDEX_NAME}'")


# Route for the home page with search form
@app.route("/")
@login_required
def home():
    return render_template("index.html")


# Route for search results
@app.route("/search")
def search():
    # Get the search query from the request parameters
    query = request.args.get("q", "")

    if not query:
        return jsonify({"hits": []})

    # Perform search in Elasticsearch
    search_results = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^2",
                        "content",
                        "author",
                    ],  # ^2 boosts the title field
                    "fuzziness": "AUTO",
                }
            },
            "highlight": {"fields": {"title": {}, "content": {}}},
        },
    )

    # Format the search results
    hits = []
    for hit in search_results["hits"]["hits"]:
        source = hit["_source"]
        highlight = hit.get("highlight", {})

        hits.append(
            {
                "id": hit["_id"],
                "title": highlight.get("title", [source["title"]])[0],
                "content": highlight.get("content", [source["content"]])[0],
                "author": source["author"],
                "date": source["date"],
                "score": hit["_score"],
            }
        )

    return jsonify({"hits": hits})


# Route for user login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form_data = request.form
        username = form_data.get("username")
        password = form_data.get("password")

        if not username or not password:
            return jsonify(
                {"success": False, "error": "Username and password are required"}
            )

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return jsonify({"success": True, "redirect": url_for("home")})
        else:
            return jsonify({"success": False, "error": "Invalid username or password"})
    return render_template("login.html", create_account_url=url_for("register"))


# Route for user registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method != "POST":
        return render_template("register.html")

    form_data = request.form
    username = form_data.get("username")
    password = form_data.get("password")

    if not username or not password:
        return jsonify(
            {"success": False, "error": "Username and password are required"}
        )

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"success": False, "error": "Username already exists"})

    new_user = User(username=username, password=password)  # type: ignore
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return jsonify({"success": True, "redirect": url_for("home")})


# Route for user logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# Set the secret key for session management
app.secret_key = os.environ.get("SECRET_KEY")

if __name__ == "__main__":
    # Create database tables
    with app.app_context():
        db.create_all()

    # Create sample data when the app starts
    create_sample_data()

    # Run the Flask app
    app.run(debug=True)
