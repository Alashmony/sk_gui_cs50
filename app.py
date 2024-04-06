from flask import Flask, session, render_template, redirect, request
from flask_session import Session

app = Flask(__name__)

# Stop permenant session
app.config["SESSION_PERMANENT"] = False
# Make session stored on the server side
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")
