from flask import Flask, url_for, render_template, session, request, redirect, flash
from flask_ckeditor import CKEditor
from tinydb import TinyDB, Query
from datetime import datetime
import requests, json, random
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'myndir')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = "sc"
ckeditor = CKEditor(app)
db = TinyDB("blogs.json")
users_db = TinyDB("users.json")
Blog = Query()
User = Query()
now = datetime.now()
data_time = now.strftime("%d/%m/%Y")

API_URL = "https://api.pokemontcg.io/v2/sets"
API_LK = {
    "X-Api-Key": "2d564b39-de51-4a1b-926f-73033816646d"
}


@app.route("/")
def index():
    response = requests.get(
        "https://api.pokemontcg.io/v2/sets?page=1&pageSize=20",
        headers=API_LK
    )
    data = response.json()
    sets = data.get("data", [])
    return render_template("index.html", sets=sets)

@app.route("/set/<set_id>")
def sets(set_id):
    response = requests.get(
        f"https://api.pokemontcg.io/v2/sets/{set_id}",
        headers=API_LK
    )
    set_data = response.json().get("data", {})
    return render_template("set.html", set=set_data)


@app.route("/leita", methods=["GET"])
def leita():
    name = request.args.get("pokemon")
    pokemons = []
    if name:
        cards = requests.get(
            "https://api.pokemontcg.io/v2/cards",
            params={"q": f"name:{name}"},
            headers=API_LK
        )
        if cards.ok:
            pokemons = cards.json().get("data", [])
    return render_template("leita.html", pokemons=pokemons)

@app.route("/pokemon/<cardid>")
def card(cardid):
    r = requests.get(
        f"https://api.pokemontcg.io/v2/cards/{cardid}",
        headers=API_LK
    )
    pokemon = r.json().get("data", {})
    return render_template("card.html", pokemon=pokemon)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if users_db.search(User.email == email):
            flash("Netfang þegar til!")
            return redirect(url_for("signup"))
        hashed_pw = generate_password_hash(password)
        users_db.insert({"email": email, "password": hashed_pw})
        flash("Nýskráning tókst! Þú getur núna skráð þig inn.")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check admin login
        if email == "admin@admin.is" and password == "123456":
            session["admin"] = True
            flash("Admin login successful!")
            return redirect(url_for("admin"))

        # Check normal users
        user = users_db.get(User.email == email)
        if user and check_password_hash(user["password"], password):
            session["user"] = email
            flash("Innskráning tókst!")
            return redirect(url_for("blog"))

        flash("Rangt netfang eða lykilorð.")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop("user", None)
    session.pop("admin", None)
    flash("Útskráning tókst.")
    return redirect(url_for('index'))

@app.route("/admin")
def admin():
    if "admin" not in session and "user" not in session:
        flash("Þú verður að vera innskráður")
        return redirect(url_for("login"))
    blogs = db.all()
    return render_template("admin.html", blogs=blogs)

@app.route("/admin/create", methods=["GET", "POST"])
def gerablog():
    if "admin" not in session and "user" not in session:
        flash("Þú verður að vera innskráður")
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        category = request.form.get("category") 
        date = datetime.now().strftime("%d/%m/%Y")

        img_file = request.files.get("image")
        img_filename = None
        if img_file and img_file.filename != "":
            img_filename = secure_filename(img_file.filename)
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], img_filename)

            # Ensure folder exists (safety net)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            img_file.save(fpath)

        if "admin" in session:
            notandi = "admin@admin.is"
        else:
            notandi = session["user"]

        if title and content and notandi:
            new_id = len(db) + 1
            db.insert({
                "id": new_id,
                "title": title,
                "content": content,
                "category": category,
                "notandi": notandi,
                "date": date,
                "image": img_filename
            })
            flash("Blog post created successfully!", "success")
            return redirect(url_for("admin"))

    return render_template("gerablog.html")


@app.route("/admin/uppfearablog/<int:blog_id>", methods=["GET", "POST"])
def uppfearablog(blog_id):
    post = db.get(Blog.id == blog_id)

    if not post:
        flash("Fann ekki bloggfærslu", "danger")
        return redirect(url_for("admin"))

    if request.method == "POST":
        db.update({
            "title": request.form.get("title"),
            "content": request.form.get("content"),
            "category": request.form.get("category"),
            "notandi": request.form.get("notandi")
        }, Blog.id == blog_id)
        flash("Blog post updated!", "info")
        return redirect(url_for("admin"))

    return render_template("uppfearablog.html", blog=post)



@app.route("/admin/eyda/<int:blog_id>")
def eyðablog(blog_id):
    db.remove(Blog.id == blog_id) 
    flash("Blog post deleted!", "danger")
    return redirect(url_for("admin"))

@app.route("/blogs")
def blog():
    blogs = db.all()
    for b in blogs:
        if b.get("image"):
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], b["image"])
            if not os.path.exists(fpath):
                b["image"] = None
    return render_template("blog.html", blogs=blogs)

@app.errorhandler(404)
def error404(e):
    return render_template("error404.html")

if __name__ == "__main__":
    app.run(debug=True)

