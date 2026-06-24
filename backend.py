import os
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher

from flask import Flask, g, jsonify, render_template, request

DATABASE = "database.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()


# lit et se connect à la DB
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


# ferme la DB lorsqu'on étein la WebApp
@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# initialise la DB
def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            importance TEXT DEFAULT 'normal',
            done INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def row_to_task(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "due_date": row["due_date"],
        "importance": row["importance"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


def get_tasks(sort_by="created_at"):
    db = get_db()

    order_by = {
        "date": "due_date = '', due_date ASC, id DESC",
        "importance": "CASE importance WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, id DESC",
        "created_at": "created_at DESC, id DESC",
    }.get(sort_by, "created_at DESC, id DESC")

    return db.execute(f"SELECT * FROM tasks ORDER BY {order_by}").fetchall()


def fuzzy_match_score(query, task):
    query = (query or "").strip().lower()
    if not query:
        return 1

    fields = [
        task["title"],
        task["description"],
        task["due_date"],
        task["importance"],
    ]
    haystack = " ".join(str(field or "") for field in fields).lower()

    if query in haystack:
        return 1

    query_words = query.split()
    haystack_words = haystack.split()

    word_scores = [
        max(
            SequenceMatcher(None, query_word, haystack_word).ratio()
            for haystack_word in haystack_words
        )
        for query_word in query_words
        if haystack_words
    ]

    if word_scores:
        return sum(word_scores) / len(word_scores)

    return SequenceMatcher(None, query, haystack).ratio()


def search_tasks(query, sort_by="created_at"):
    tasks = get_tasks(sort_by)
    query = (query or "").strip()
    if not query:
        return tasks

    scored_tasks = [(fuzzy_match_score(query, task), task) for task in tasks]
    return [
        task
        for score, task in sorted(scored_tasks, key=lambda item: item[0], reverse=True)
        if score >= 0.6
    ]


@app.route("/")
def home():
    return render_template("home.html", tasks=get_tasks())


@app.route("/search")
def search():
    tasks = search_tasks(
        request.args.get("q", ""),
        request.args.get("sort", "created_at"),
    )
    return render_template("_tasks.html", tasks=tasks)


@app.route("/sort")
def sort_tasks():
    tasks = get_tasks(request.args.get("by", "created_at"))
    return render_template("_tasks.html", tasks=tasks)


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return "", 200


# ce qui permet d'ajouter des tasks en faisant des requettes POST à /add
@app.route("/add", methods=["POST"])
def add_task():
    data = request.get_json(silent=True) or request.form

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Le champ title est obligatoire."}), 400

    description = (data.get("description") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    importance = (data.get("importance") or "normal").strip()
    created_at = datetime.now().isoformat(timespec="seconds")

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO tasks (title, description, due_date, importance, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, description, due_date, importance, created_at),
    )
    db.commit()

    task = db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()

    if request.headers.get("HX-Request"):
        return render_template("_task.html", task=task), 201

    return jsonify(row_to_task(task)), 201


init_db()

if __name__ == "__main__":
    app.run(debug=True)
