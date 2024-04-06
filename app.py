from flask import Flask, session, render_template, redirect, request
from flask_session import Session
from werkzeug.utils import secure_filename
import pandas as pd
import uuid
import helpers
import os
from ydata_profiling import ProfileReport
from bs4 import BeautifulSoup

# import duckdb

app = Flask(__name__)
accepted_ext = ["csv", "xls", "xlsx"]


# stop cashing
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Stop permenant session
app.config["SESSION_PERMANENT"] = False
# Make session stored on the server side
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/manipulate", methods=["GET", "POST"])
def manipulate():
    df = session["df"]["v0"]
    rows = df.head(10).to_dict(orient="records")
    columns = list(session["df"]["v0"].columns)
    file = session["filename"]
    return render_template("manipulate.html", file=file, rows=rows, columns=columns)


@app.route("/explore")
def explore():
    # Create a dataprep report
    report_location = "templates/" + str(session["uid"]) + "/"
    try:
        os.mkdir(report_location)
    except:
        pass
    report_path = report_location + session["filename"] + ".html"
    print(report_path)

    if not os.path.exists(report_path):
        ProfileReport(session["df"]["v0"]).to_file(report_path)

    # Remove navigation bar to keep mine
    with open(report_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")
    soup.body.a.decompose()
    soup.body.nav.decompose()

    new_path = report_path.replace(".html", "_clean.html")
    # Save new file
    with open(new_path, "w", encoding="utf-8") as new_file:
        new_file.write(str(soup))
    session["report_location"] = report_location
    session["report_path"] = new_path

    return render_template("explore.html", report=new_path[new_path.find("/") :])


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        # Let's get the extension
        file = request.files["file"]

        # if no files provided
        if not file:
            error = "No files was choosen, please choose a file!"
            return render_template("upload.html", exts=accepted_ext, error=error)

        filename = secure_filename(file.filename)
        filename_inverted = filename[::-1]
        ext = filename_inverted[: filename_inverted.find(".")][::-1]

        # if the provided extension is not in the accepted ones
        if ext.lower() not in accepted_ext:
            error = "Unacceptable format!"
            return render_template("upload.html", exts=accepted_ext, error=error)

        # store data file name in session
        session["filename"] = filename
        session["uid"] = uuid.uuid4()

        # initiate datafolder to store session details
        print(session)
        session["location"] = "datasets/" + str(session["uid"]) + "/"
        os.mkdir(session["location"])
        location = session["location"] + filename

        # Store data in the specified location
        session["dataset_location"] = location
        file.save(location)

        # Read data into the dataframe
        if ext == "csv":
            df = pd.read_csv(location, low_memory=False)
        if ext == "xlsx" or ext == "xls":
            df = pd.read_excel(location)
        session["df"] = {"v0": df}
        columns = list(df.columns)
        rows = df.head(10).to_dict(orient="records")
        # print(rows)
        return render_template("upload.html", file=filename, columns=columns, rows=rows)
    return render_template("upload.html", exts=accepted_ext)
