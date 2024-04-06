from flask import Flask, session, render_template, redirect
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
