from flask import Flask, session, render_template, redirect, request, url_for
from flask_session import Session
from werkzeug.utils import secure_filename
import pandas as pd
import uuid
from helpers import *
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
    return render_template("index.html")


@app.route("/remove_steps", methods=["POST"])
def remove_steps():
    # Find step to remove
    step = request.form.get("step_to_remove")
    step_name = list(session["steps"][-1].keys())[0]
    step_n = int(step_name[step_name.find("_") + 1 :])
    steps = []
    dfs = {}
    # To reset all the proccess
    if step == "":
        session["steps"] = []
        session["df"] = {"v0": session["df"]["v0"]}
    # If the step # provided is more than the latest step
    elif int(step) > step_n:
        return redirect(url_for("manipulate", error_msg="This step is not found"))
    else:
        # try to perform calculations to the main df without this step
        try:
            # reapply all steps
            last_step = 0
            for step_dict in session["steps"]:
                step_name = list(step_dict.keys())[0]
                step_code = step_dict[step_name]
                print(step_name, step_code)
                # Get current step #
                step_number = int(step_name[step_name.find("_") + 1 :])
                # if this is the removed step
                if step_number == int(step):
                    continue
                # reapply step and store the df
                else:
                    dfs["v0"] = session["df"]["v0"]
                    df = dfs["v" + str(last_step)]
                    dfs["v" + str(step_number)] = eval(step_code)
                    steps.append({step_name: step_code})
                    last_step = step_number
            session["steps"] = steps
            session["df"] = dfs
        except Exception as e:
            return redirect(url_for("manipulate", error_msg=str(e)))
    return redirect("/manipulate")


@app.route("/manipulate", methods=["GET", "POST"])
def manipulate():
    # Create steps to store the steps
    if "steps" not in session or len(session["steps"]) == 0:
        session["steps"] = []
        step_n = 1
    else:
        step_name = list(session["steps"][-1].keys())[0]
        step_n = int(step_name[step_name.find("_") + 1 :]) + 1

    if request.method == "GET":
        step_n -= 1

    error_msg = request.args.get("error_msg")

    # If a new step was sent
    if request.method == "POST":
        func = request.form.get("function")
        args = request.form.get("code")
        close = request.form.get("close")
        # print(func, args, close)
        step = func + args + close

        # Find if inplace is used to remove it
        try:
            step = step.replace(" ,", ",").replace("  ", " ").replace(", ", ",")
            step = step.replace(
                step[step.find("inplace") : step.find(",", step.find("inplace")) + 1],
                "",
            )
            step = step.replace(
                step[step.find("inplace") : step.find(")", step.find("inplace"))], ""
            )
            step = step.replace(",)", ")")
        except:
            pass

        # Check if it is not a duplicated step  or a refresh
        if step_n == 1 or step != list(session["steps"][-1].values())[0]:
            df = session["df"]["v" + str(step_n - 1)]
            session["steps"].append({"step_" + str(step_n): step})
            session["df"]["v" + str(step_n)] = eval(step)

    file = session["filename"]

    # If the tranformations leaded to a new DF, not a different type
    try:
        columns = list(session["df"]["v" + str(step_n)].columns)
        rows = session["df"]["v" + str(step_n)].head(10).to_dict(orient="records")
        methods_ = get_methods(session["df"]["v" + str(step_n)])
    except:
        columns = list(session["df"]["v0"].columns)
        rows = session["df"]["v0"].head(10).to_dict(orient="records")
        methods_ = get_methods(session["df"]["v0"])
    # print(session["steps"])
    params = {
        "file": file,
        "rows": rows,
        "columns": columns,
        "methods_": methods_.keys(),
        "descriptions": methods_,
        "columnsize": len(columns),
    }
    if len(session["steps"]) > 0:
        params["applied_steps"] = session["steps"]
    if error_msg != None:
        params["error_msg"] = error_msg
    return render_template("manipulate.html", **params)


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
