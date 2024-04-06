from flask import Flask, session, render_template, redirect, request
from flask_session import Session
from werkzeug.utils import secure_filename
import pandas as pd
import os

app = Flask(__name__)
accepted_ext = ["csv", "xls", "xlsx"]

df = pd.DataFrame()

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
        location = "datasets/" + filename
        file.save(location)
        # Read data into the dataframe
        if ext == "csv":
            df = pd.read_csv(location, low_memory=False)
        if ext == "xlsx" or ext == "xls":
            df = pd.read_excel(location)

        columns = list(df.columns)
        rows = df.head(10).to_dict(orient="records")
        # print(rows)
        return render_template("upload.html", file=filename, columns=columns, rows=rows)

    return render_template("upload.html", exts=accepted_ext)
