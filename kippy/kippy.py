import os
import sqlite3
from datetime import datetime
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, "kippy.db"),
    SECRET_KEY=os.urandom(16),
    USERNAME="admin",
    PASSWORD="default"
))

app.config.from_envvar("FLASKR_SETTINGS", silent=True)
imgdir = "static/images/animals" # Image directory path from root of server.

def connect_db():
    rv = sqlite3.connect(app.config["DATABASE"])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    if not hasattr(g, "sqlite_db"):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "sqlite_db"):
        g.sqlite_db.close()

def db_init():
    global imgdir
    db = get_db()

    with app.open_resource("schema.sql", mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

    # Get a list of all image files.
    images = [f for f in os.listdir(imgdir) if os.path.isfile(os.path.join(imgdir, f))]
    cur = db.cursor().execute("select * from images") # Find all images in db.
    entries = [entry[0] for entry in cur.fetchall()] # Get image names.

    cur = db.cursor()
    # Add image files to db if they do not exist.
    for image in images:
        if image[:-4] not in entries:
            cur.execute("insert into images values(?, ?, ?)", (image[:-4], "cat" if image[:1] == 'k' else "dog", image))

    db.commit() # Save results!

@app.cli.command("dbinit")
def initdb_command():
    db_init()
    print("Database initialized.")

def track_user():
    db = get_db()

    # Get column names from tracking table in db.
    cur = db.cursor().execute("select * from tracking")
    col_names = [desc[0] for desc in cur.description]
    col_names.remove("req_id")

    # Build list of header contents.
    req_headers = []
    for col in col_names:
        if col in request.headers:
            req_headers.append(request.headers[col])
        else:
            req_headers.append("")

    req_headers[-2] = repr(datetime.now()) # Set last entry as current date.
    req_headers[-1] = request.url
    # Build query string.
    query = "insert into tracking(" + ", ".join(col_names) + ") "
    query += "values(" + "?, " * (len(col_names) - 1) + "?)"

    cur = db.cursor().execute(query, req_headers) # Insert tracking data.
    db.commit()

@app.route('/')
def show_home():
    global imgdir
    db = get_db()

    track_user()

    # Get image data from db.
    cur = db.cursor().execute("select * from images order by name")
    entries = cur.fetchall()

    return render_template('show_home.html', entries = entries, imgpath = imgdir)

@app.route('/img/<img>')
def show_image(img):
    global imgdir
    db = get_db()

    # Get image info from the db.
    cur = db.cursor().execute("select * from images where name=?", (img, ))
    image = cur.fetchall()

    track_user()

    if image: # Display proper page.
        return render_template("show_image.html", images = image, imgpath = imgdir);
    else: # Bail out.
        abort(404)
