from flask import Flask, session, render_template, redirect, request, url_for, flash
from flask_session import Session
from werkzeug.utils import secure_filename
import pandas as pd
import uuid
from helpers import *
import os
import shutil
from datetime import datetime, timedelta
import time
from ydata_profiling import ProfileReport
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# import duckdb

app = Flask(__name__)
app.secret_key = os.urandom(24)
accepted_ext = ["csv", "xls", "xlsx"]
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB

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

# Cleanup function to remove old files and reports
def cleanup_old_data(days=7):
    """Remove files and reports older than specified days"""
    cutoff = datetime.now() - timedelta(days=days)
    for folder in ['datasets', 'templates']:
        if os.path.exists(folder):
            for uuid_folder in os.listdir(folder):
                if uuid_folder not in ['index.html', 'upload.html', 'layout.html', 'manipulate.html', 'explore.html', 'login.html', 'register.html', 'dashboard.html']:
                    path = os.path.join(folder, uuid_folder)
                    if os.path.isdir(path):
                        try:
                            folder_time = datetime.fromtimestamp(os.path.getctime(path))
                            if folder_time < cutoff:
                                shutil.rmtree(path)
                                print(f"Removed old data: {path}")
                        except Exception as e:
                            print(f"Error cleaning up {path}: {str(e)}")

# Schedule cleanup to run periodically
@app.before_request
def before_request():
    # Run cleanup once a day (check based on timestamp file)
    timestamp_file = "last_cleanup.txt"
    run_cleanup = False
    
    if not os.path.exists(timestamp_file):
        run_cleanup = True
    else:
        with open(timestamp_file, "r") as f:
            try:
                last_time = float(f.read().strip())
                if time.time() - last_time > 86400:  # 24 hours
                    run_cleanup = True
            except:
                run_cleanup = True
    
    if run_cleanup:
        cleanup_old_data()
        with open(timestamp_file, "w") as f:
            f.write(str(time.time()))

@app.route("/")
def home():
    # Initialize database if it doesn't exist
    if not os.path.exists('sk_gui.db'):
        init_db()
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return render_template("login.html", error="Username is required")

        # Ensure password was submitted
        elif not password:
            return render_template("login.html", error="Password is required")

        # Query database for username
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        # Ensure username exists and password is correct
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        # Redirect user to home page
        flash("You have been logged in successfully!")
        return redirect("/dashboard")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure all fields are filled
        if not username:
            return render_template("register.html", error="Username is required")
        elif not email:
            return render_template("register.html", error="Email is required")
        elif not password:
            return render_template("register.html", error="Password is required")
        elif not confirmation:
            return render_template("register.html", error="Please confirm your password")

        # Ensure passwords match
        if password != confirmation:
            return render_template("register.html", error="Passwords do not match")

        # Generate hash
        hash = generate_password_hash(password)

        # Add user to database
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, hash)
            )
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username or email already exists")

        # Redirect to login page
        flash("Registration successful! Please log in.")
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    """Show user's projects"""
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect("/login")
    
    # Get user's projects
    conn = get_db_connection()
    projects = conn.execute(
        "SELECT * FROM projects WHERE user_id = ? ORDER BY last_modified DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    
    return render_template("dashboard.html", projects=projects, username=session["username"])


@app.route("/create_project", methods=["POST"])
def create_project():
    """Create a new project"""
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect("/login")
    
    project_name = request.form.get("project_name")
    description = request.form.get("description", "")
    
    if not project_name:
        flash("Project name is required")
        return redirect("/dashboard")
    
    # Generate UUID for the project
    project_uuid = str(uuid.uuid4())
    
    # Add project to database
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO projects (user_id, name, description, uuid) 
           VALUES (?, ?, ?, ?)""",
        (session["user_id"], project_name, description, project_uuid)
    )
    conn.commit()
    
    # Get the newly created project
    project = conn.execute(
        "SELECT * FROM projects WHERE uuid = ?",
        (project_uuid,)
    ).fetchone()
    conn.close()
    
    # Create project directory
    project_dir = f"datasets/{project_uuid}"
    os.makedirs(project_dir, exist_ok=True)
    
    session["current_project_id"] = project["id"]
    session["current_project_name"] = project_name
    
    return redirect("/upload")


@app.route("/project/<uuid>")
def load_project(uuid):
    """Load a project by UUID"""
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect("/login")
    
    # Verify the project belongs to the user
    conn = get_db_connection()
    project = conn.execute(
        "SELECT * FROM projects WHERE uuid = ? AND user_id = ?",
        (uuid, session["user_id"])
    ).fetchone()
    
    if not project:
        flash("Project not found or you don't have permission to access it")
        return redirect("/dashboard")
    
    # Get all dataframes in the project
    dataframes = conn.execute(
        "SELECT * FROM dataframes WHERE project_id = ?",
        (project["id"],)
    ).fetchall()
    
    # Update session with project info
    session["current_project_id"] = project["id"]
    session["current_project_name"] = project["name"]
    
    # If project has dataframes, load the first one
    if dataframes:
        session["current_dataframe_id"] = dataframes[0]["id"]
        
        # Get steps for the dataframe
        steps = conn.execute(
            "SELECT * FROM steps WHERE dataframe_id = ? ORDER BY step_number",
            (dataframes[0]["id"],)
        ).fetchall()
        
        # Load dataframe from file
        df_path = dataframes[0]["data_path"]
        if df_path.endswith('.csv'):
            df = pd.read_csv(df_path, low_memory=False)
        elif df_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(df_path)
            
        # Store dataframe in session
        session["df"] = {"v0": df}
        session["steps"] = []
        
        # Apply all steps
        current_df = df
        for step in steps:
            step_code = step["step_code"]
            step_num = step["step_number"]
            df = eval(step_code)
            session["df"][f"v{step_num}"] = df
            session["steps"].append({f"step_{step_num}": step_code})
        
        # Update last accessed timestamp
        conn.execute(
            "UPDATE projects SET last_modified = datetime('now') WHERE id = ?",
            (project["id"],)
        )
        conn.commit()
    
    conn.close()
    
    return redirect("/manipulate")


@app.route("/remove_steps", methods=["POST"])
def remove_steps():
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect("/login")
        
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
        
        # Clear steps from database if user is logged in
        if "current_dataframe_id" in session:
            conn = get_db_connection()
            conn.execute("DELETE FROM steps WHERE dataframe_id = ?", 
                        (session["current_dataframe_id"],))
            conn.commit()
            conn.close()
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
                # Get current step #
                step_number = int(step_name[step_name.find("_") + 1 :])
                # if this is the removed step
                if step_number == int(step):
                    # Remove step from database if user is logged in
                    if "current_dataframe_id" in session:
                        conn = get_db_connection()
                        conn.execute("DELETE FROM steps WHERE dataframe_id = ? AND step_number = ?", 
                                    (session["current_dataframe_id"], step_number))
                        conn.commit()
                        conn.close()
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
    # Redirect if not authenticated and trying to access project data
    if "current_project_id" in session and "user_id" not in session:
        return redirect("/login")
    
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

        # Check if it is not a duplicated step or a refresh
        if step_n == 1 or step != list(session["steps"][-1].values())[0]:
            df = session["df"]["v" + str(step_n - 1)]
            try:
                result = eval(step)
                session["steps"].append({"step_" + str(step_n): step})
                session["df"]["v" + str(step_n)] = result
                
                # If user is logged in, save step to database
                if "current_dataframe_id" in session:
                    conn = get_db_connection()
                    conn.execute(
                        """INSERT INTO steps (dataframe_id, step_number, step_code, dataframe_version)
                           VALUES (?, ?, ?, ?)""",
                        (session["current_dataframe_id"], step_n, step, f"v{step_n}")
                    )
                    conn.commit()
                    conn.close()
            except Exception as e:
                error_msg = str(e)

    file = session["filename"]

    # If the transformations led to a new DF, not a different type
    try:
        current_df = session["df"]["v" + str(step_n)]
        columns = list(current_df.columns)
        rows = current_df.head(10).to_dict(orient="records")
        methods_ = get_methods(current_df)
        
        # Get Series operations for column level manipulations
        if len(columns) > 0:
            first_col = current_df[columns[0]]
            series_methods = get_methods(first_col)
        else:
            series_methods = {}
    except:
        current_df = session["df"]["v0"]
        columns = list(current_df.columns)
        rows = current_df.head(10).to_dict(orient="records")
        methods_ = get_methods(current_df)
        
        # Get Series operations for column level manipulations
        if len(columns) > 0:
            first_col = current_df[columns[0]]
            series_methods = get_methods(first_col)
        else:
            series_methods = {}
    
    # Check if user is authenticated
    is_authenticated = "user_id" in session
    
    params = {
        "file": file,
        "rows": rows,
        "columns": columns,
        "descriptions": methods_,(),
        "columnsize": len(columns),
        "is_authenticated": is_authenticated,
        "series_methods": series_methods,ted,
    }   "series_methods": series_methods,
    }
    if "current_project_id" in session:
        params["project_name"] = session.get("current_project_name", "")
        params["project_name"] = session.get("current_project_name", "")
        # Get all dataframes in the project
        conn = get_db_connection()e project
        dataframes = conn.execute(
            "SELECT * FROM dataframes WHERE project_id = ?",
            (session["current_project_id"],)project_id = ?",
        ).fetchall()["current_project_id"],)
        conn.close()
        conn.close()
        if dataframes:
            params["dataframes"] = dataframes
            params["current_dataframe_id"] = session.get("current_dataframe_id")
            params["current_dataframe_id"] = session.get("current_dataframe_id")
    if len(session["steps"]) > 0:
        params["applied_steps"] = session["steps"]
    if error_msg != None:teps"] = session["steps"]
        params["error_msg"] = error_msg
        params["error_msg"] = error_msg
    return render_template("manipulate.html", **params)
    return render_template("manipulate.html", **params)

@app.route("/explore")
def explore():xplore")
    # Create a dataprep report
    report_location = "templates/" + str(session["uid"]) + "/"
    try:rt_location = "templates/" + str(session["uid"]) + "/"
        os.mkdir(report_location)
    except:mkdir(report_location)
        pass
    report_path = report_location + session["filename"] + ".html"
    print(report_path)rt_location + session["filename"] + ".html"
    print(report_path)
    if not os.path.exists(report_path):
        ProfileReport(session["df"]["v0"]).to_file(report_path)
        ProfileReport(session["df"]["v0"]).to_file(report_path)
    # Remove navigation bar to keep mine
    with open(report_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")
    soup.body.a.decompose()p(file, "html.parser")
    soup.body.nav.decompose()
    soup.body.nav.decompose()
    new_path = report_path.replace(".html", "_clean.html")
    # Save new filert_path.replace(".html", "_clean.html")
    with open(new_path, "w", encoding="utf-8") as new_file:
        new_file.write(str(soup))ding="utf-8") as new_file:
    session["report_location"] = report_location
    session["report_path"] = new_pathrt_location
    session["report_path"] = new_path
    return render_template("explore.html", report=new_path[new_path.find("/") :])
    return render_template("explore.html", report=new_path[new_path.find("/") :])

@app.route("/upload", methods=["GET", "POST"])
def upload():upload", methods=["GET", "POST"])
    # Check if user is logged in
    is_authenticated = "user_id" in session
    is_authenticated = "user_id" in session
    if request.method == "POST":
        # Let's get the extension
        file = request.files["file"]
        file = request.files["file"]
        # if no files provided
        if not file:s provided
            error = "No file was chosen, please choose a file!"
            return render_template("upload.html", exts=accepted_ext, error=error)
            return render_template("upload.html", exts=accepted_ext, error=error)
        filename = secure_filename(file.filename)
        filename_inverted = filename[::-1]lename)
        ext = filename_inverted[: filename_inverted.find(".")][::-1]
        ext = filename_inverted[: filename_inverted.find(".")][::-1]
        # if the provided extension is not in the accepted ones
        if ext.lower() not in accepted_ext:in the accepted ones
            error = "Unacceptable format!":
            return render_template("upload.html", exts=accepted_ext, error=error)
            return render_template("upload.html", exts=accepted_ext, error=error)
        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)= file.tell()
        if file_length > MAX_FILE_SIZE_MB * 1024 * 1024:
            error = f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB} MB!"
            return render_template("upload.html", exts=accepted_ext, error=error)B!"
            return render_template("upload.html", exts=accepted_ext, error=error)
        # Generate UUID for this dataset or use project UUID if available
        if "current_project_id" in session: use project UUID if available
            conn = get_db_connection()sion:
            project = conn.execute(n()
                "SELECT uuid FROM projects WHERE id = ?", 
                (session["current_project_id"],) id = ?", 
            ).fetchone()["current_project_id"],)
            session["uid"] = project["uuid"]
        else:ession["uid"] = project["uuid"]
            session["uid"] = uuid.uuid4()
            session["uid"] = uuid.uuid4()
        # Store data file name in session
        session["filename"] = filenameion
        session["filename"] = filename
        # Create directory if it doesn't exist
        session["location"] = "datasets/" + str(session["uid"]) + "/"
        os.makedirs(session["location"], exist_ok=True)["uid"]) + "/"
        location = session["location"] + filename=True)
        location = session["location"] + filename
        # Store data in the specified location
        session["dataset_location"] = location
        file.save(location)cation"] = location
        file.save(location)
        # Read data into the dataframe
        if ext == "csv": the dataframe
            df = pd.read_csv(location, low_memory=False)
        if ext == "xlsx" or ext == "xls":w_memory=False)
            df = pd.read_excel(location):
            df = pd.read_excel(location)
        # Store dataframe in session
        session["df"] = {"v0": df}on
        session["steps"] = []: df}
        session["steps"] = []
        # If logged in, save dataframe info to database
        if "current_project_id" in session: to database
            # Create a name for the DataFrame (use filename without extension)
            df_name = os.path.splitext(filename)[0]filename without extension)
            df_name = os.path.splitext(filename)[0]
            conn = get_db_connection()
            conn.execute(_connection()
                """INSERT INTO dataframes (project_id, name, description, data_path)
                   VALUES (?, ?, ?, ?)""",(project_id, name, description, data_path)
                (session["current_project_id"], df_name, "", location)
            )   (session["current_project_id"], df_name, "", location)
            conn.commit()
            conn.commit()
            # Get the newly created dataframe ID
            dataframe = conn.execute(ataframe ID
                "SELECT id FROM dataframes WHERE project_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
                (session["current_project_id"], df_name)_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
            ).fetchone()["current_project_id"], df_name)
            ).fetchone()
            session["current_dataframe_id"] = dataframe["id"]
            conn.close()rent_dataframe_id"] = dataframe["id"]
            conn.close()
        columns = list(df.columns)
        rows = df.head(10).to_dict(orient="records")
        rows = df.head(10).to_dict(orient="records")
        # If logged in, show option to add as new dataframe to project
        params = {d in, show option to add as new dataframe to project
            "file": filename, 
            "columns": columns, 
            "rows": rows,lumns, 
            "is_authenticated": is_authenticated
        }   "is_authenticated": is_authenticated
        }
        if "current_project_id" in session:
            params["project_name"] = session.get("current_project_name", "")
            params["project_name"] = session.get("current_project_name", "")
        return render_template("upload.html", **params)
        return render_template("upload.html", **params)
    # For GET requests
    params = {"exts": accepted_ext, "is_authenticated": is_authenticated}
    params = {"exts": accepted_ext, "is_authenticated": is_authenticated}
    if "current_project_id" in session:
        params["project_name"] = session.get("current_project_name", "")
        params["project_name"] = session.get("current_project_name", "")
        # If in a project, show existing dataframes
        conn = get_db_connection()isting dataframes
        dataframes = conn.execute(
            "SELECT * FROM dataframes WHERE project_id = ?",
            (session["current_project_id"],)project_id = ?",
        ).fetchall()["current_project_id"],)
        conn.close()
        conn.close()
        if dataframes:
            params["dataframes"] = dataframes
            params["dataframes"] = dataframes
    return render_template("upload.html", **params)
    return render_template("upload.html", **params)

@app.route("/column_operation", methods=["POST"])
def column_operation():ration", methods=["POST"])
    """Perform operations on a single column/Series"""
    column_name = request.form.get("column_name")es"""
    operation = request.form.get("operation")me")
    operation = request.form.get("operation")
    if not column_name or not operation:
        return redirect(url_for("manipulate", error_msg="Column name and operation are required"))
        return redirect(url_for("manipulate", error_msg="Column name and operation are required"))
    # Get the latest dataframe version
    if "steps" in session and len(session["steps"]) > 0:
        step_name = list(session["steps"][-1].keys())[0]
        step_n = int(step_name[step_name.find("_") + 1 :])
        df = session["df"][f"v{step_n}"].find("_") + 1 :])
    else:f = session["df"][f"v{step_n}"]
        df = session["df"]["v0"]
        step_n = 0on["df"]["v0"]
        step_n = 0
    # Get additional parameters based on operation
    kwargs = {}ional parameters based on operation
    if operation == "fill_na":
        kwargs["value"] = request.form.get("value", 0)
    elif operation == "replace":t.form.get("value", 0)
        kwargs["to_replace"] = request.form.get("to_replace")
        kwargs["value"] = request.form.get("value")_replace")
    elif operation in ["map", "apply"]:get("value")
        kwargs["function"] = request.form.get("function")
    elif operation == "astype":quest.form.get("function")
        kwargs["dtype"] = request.form.get("dtype")
        kwargs["dtype"] = request.form.get("dtype")
    try:
        # Perform the operation on the column
        series = df[column_name]on the column
        result = perform_series_operation(series, operation, **kwargs)
        result = perform_series_operation(series, operation, **kwargs)
        # Update the dataframe with the new column
        new_df = df.copy()rame with the new column
        if operation in ["describe", "value_counts", "unique"]:
            # These operations return a new series, don't update the dataframe
            # Instead, show the result in a separate view update the dataframe
            session["series_result"] = result.to_dict()ew
            return redirect(url_for("series_result", column=column_name, operation=operation))
        else:eturn redirect(url_for("series_result", column=column_name, operation=operation))
            new_df[column_name] = result
            new_df[column_name] = result
        # Create a step code that represents this operation
        step_code = f"df.copy()"t represents this operation
        if kwargs:= f"df.copy()"
            kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            step_code = f"df.copy(); df['{column_name}'] = perform_series_operation(df['{column_name}'], '{operation}', {kwargs_str})"
        else:tep_code = f"df.copy(); df['{column_name}'] = perform_series_operation(df['{column_name}'], '{operation}', {kwargs_str})"
            step_code = f"df.copy(); df['{column_name}'] = perform_series_operation(df['{column_name}'], '{operation}')"
            step_code = f"df.copy(); df['{column_name}'] = perform_series_operation(df['{column_name}'], '{operation}')"
        # Add the step
        session["steps"].append({f"step_{step_n + 1}": step_code})
        session["df"][f"v{step_n + 1}"] = new_df+ 1}": step_code})
        session["df"][f"v{step_n + 1}"] = new_df
        # If user is logged in, save step to database
        if "current_dataframe_id" in session:database
            conn = get_db_connection()ession:
            conn.execute(_connection()
                """INSERT INTO steps (dataframe_id, step_number, step_code, dataframe_version)
                   VALUES (?, ?, ?, ?)""",frame_id, step_number, step_code, dataframe_version)
                (session["current_dataframe_id"], step_n + 1, step_code, f"v{step_n + 1}")
            )   (session["current_dataframe_id"], step_n + 1, step_code, f"v{step_n + 1}")
            conn.commit()
            conn.close())
            conn.close()
        return redirect("/manipulate")
    except Exception as e:manipulate")
        return redirect(url_for("manipulate", error_msg=str(e)))
        return redirect(url_for("manipulate", error_msg=str(e)))

@app.route("/series_result")
def series_result():result")
    """Show the result of a series operation"""
    column = request.args.get("column", "")n"""
    operation = request.args.get("operation", "")
    operation = request.args.get("operation", "")
    if "series_result" not in session:
        return redirect("/manipulate")
        return redirect("/manipulate")
    result = session["series_result"]
    result = session["series_result"]
    return render_template("series_result.html", 
                         column=column, t.html", 
                         operation=operation, 
                         result=result)ation, 
                         result=result)

@app.route("/switch_dataframe/<int:dataframe_id>")
def switch_dataframe(dataframe_id):dataframe_id>")
    """Switch to another dataframe in the current project"""
    # Ensure user is logged inrame in the current project"""
    if "user_id" not in session or "current_project_id" not in session:
        return redirect("/login")r "current_project_id" not in session:
        return redirect("/login")
    # Get the dataframe info
    conn = get_db_connection()
    dataframe = conn.execute()
        "SELECT * FROM dataframes WHERE id = ? AND project_id = ?",
        (dataframe_id, session["current_project_id"])oject_id = ?",
    ).fetchone()me_id, session["current_project_id"])
    ).fetchone()
    if not dataframe:
        flash("Dataframe not found or you don't have permission to access it")
        return redirect("/dashboard") you don't have permission to access it")
        return redirect("/dashboard")
    # Get steps for the dataframe
    steps = conn.execute(ataframe
        "SELECT * FROM steps WHERE dataframe_id = ? ORDER BY step_number",
        (dataframe_id,)steps WHERE dataframe_id = ? ORDER BY step_number",
    ).fetchall()me_id,)
    ).fetchall()
    # Load dataframe from file
    df_path = dataframe["data_path"]
    if df_path.endswith('.csv'):th"]
        df = pd.read_csv(df_path, low_memory=False)
    elif df_path.endswith(('.xlsx', '.xls')):False)
        df = pd.read_excel(df_path) '.xls')):
        df = pd.read_excel(df_path)
    # Update session
    session["current_dataframe_id"] = dataframe_id
    session["filename"] = os.path.basename(df_path)
    session["df"] = {"v0": df}ath.basename(df_path)
    session["steps"] = []: df}
    session["steps"] = []
    # Apply all steps
    for step in steps:
        step_code = step["step_code"]
        step_num = step["step_number"]
        try:_num = step["step_number"]
            result_df = eval(step_code)
            session["df"][f"v{step_num}"] = result_df
            session["steps"].append({f"step_{step_num}": step_code})
        except Exception as e:ppend({f"step_{step_num}": step_code})
            flash(f"Error applying step {step_num}: {str(e)}")
            flash(f"Error applying step {step_num}: {str(e)}")
    conn.close()
    return redirect("/manipulate")
    return redirect("/manipulate")

@app.route("/add_dataframe", methods=["POST"])
def add_dataframe():aframe", methods=["POST"])
    """Add a new dataframe to the current project"""
    # Ensure user is logged in and has a current project
    if "user_id" not in session or "current_project_id" not in session:
        return redirect("/login")r "current_project_id" not in session:
        return redirect("/login")
    df_name = request.form.get("df_name")
    df_name = request.form.get("df_name")
    if not df_name:
        flash("DataFrame name is required")
        return redirect("/upload")equired")
        return redirect("/upload")
    # Create a new dataframe by copying the current one
    if "df" not in session:frame by copying the current one
        return redirect("/upload")
    
    # Get the latest version of the dataframe
    if "steps" in session and len(session["steps"]) > 0:
        step_name = list(session["steps"][-1].keys())[0].find("_") + 1 :])
        step_n = int(step_name[step_name.find("_") + 1 :])f = session["df"][f"v{step_n}"]
        df = session["df"][f"v{step_n}"]
    else:df = session["df"]["v0"]
        df = session["df"]["v0"]
        
    # Save the dataframe to a new file
    project_uuid = str(session["uid"])uid}/{df_name}.csv"
    new_df_path = f"datasets/{project_uuid}/{df_name}.csv"df.to_csv(new_df_path, index=False)
    df.to_csv(new_df_path, index=False)
    
    # Add to database_connection()
    conn = get_db_connection()
    conn.execute((project_id, name, description, data_path)
        """INSERT INTO dataframes (project_id, name, description, data_path)
           VALUES (?, ?, ?, ?)""",   (session["current_project_id"], df_name, "", new_df_path)
        (session["current_project_id"], df_name, "", new_df_path)
    )conn.commit()
    conn.commit()
    rame
    # Switch to the new dataframe
    dataframe = conn.execute(_id = ? AND name = ? ORDER BY id DESC LIMIT 1",
        "SELECT id FROM dataframes WHERE project_id = ? AND name = ? ORDER BY id DESC LIMIT 1",["current_project_id"], df_name)
        (session["current_project_id"], df_name)
    ).fetchone()conn.close()
    conn.close()
        return redirect(url_for("switch_dataframe", dataframe_id=dataframe["id"]))
    return redirect(url_for("switch_dataframe", dataframe_id=dataframe["id"]))
    ble to copy")
    flash("No dataframe available to copy")    return redirect("/upload")
    return redirect("/upload")

"/plot", methods=["GET", "POST"])
@app.route("/plot", methods=["GET", "POST"])
def plot():"
    """Create plots using matplotlib"""
    # Get the latest dataframe version
    if "steps" in session and len(session["steps"]) > 0:
        step_name = list(session["steps"][-1].keys())[0].find("_") + 1 :])
        step_n = int(step_name[step_name.find("_") + 1 :])f = session["df"][f"v{step_n}"]
        df = session["df"][f"v{step_n}"]
    else:    df = session["df"]["v0"]
        df = session["df"]["v0"]
    
    if request.method == "POST":")
        plot_type = request.form.get("plot_type")
        x_column = request.form.get("x_column")
        y_column = request.form.get("y_column")title = request.form.get("title", f"{plot_type.capitalize()} Plot")
        title = request.form.get("title", f"{plot_type.capitalize()} Plot")
        t_type != 'hist' and not y_column):
        if not plot_type or not x_column or (plot_type != 'hist' and not y_column):
            return render_template("plot.html", 
                                 columns=df.columns.tolist(),                         error="Please select all required fields")
                                 error="Please select all required fields")
        
        try:mn, y_column, plot_type, title)
            plot_data = generate_plot(df, x_column, y_column, plot_type, title)
            return render_template("plot.html", olist(),
                                 columns=df.columns.tolist(),,
                                 plot_data=plot_data,
                                 current_x=x_column,
                                 current_y=y_column,pe,
                                 current_type=plot_type,   current_title=title)
                                 current_title=title)
        except Exception as e:
            return render_template("plot.html", lumns.tolist(),
                                 columns=df.columns.tolist(),                             error=str(e))
                                 error=str(e))
    
    # For GET requests    return render_template("plot.html", columns=df.columns.tolist())
    return render_template("plot.html", columns=df.columns.tolist())

ication
# Initialize the application
def initialize_app():ation by creating necessary directories and database"""
    """Initialize the application by creating necessary directories and database"""
    # Ensure database existsh.exists('sk_gui.db'):
    if not os.path.exists('sk_gui.db'):
        init_db()    print("Database initialized")
        print("Database initialized")
    
    # Ensure required directories existuser_reports']:
    for directory in ['datasets', 'templates/user_reports']:
        os.makedirs(directory, exist_ok=True)    print(f"Directory {directory} checked/created")
        print(f"Directory {directory} checked/created")
    
    # Initialize cleanup timestamp file
    timestamp_file = "last_cleanup.txt"
    if not os.path.exists(timestamp_file):) as f:
        with open(timestamp_file, "w") as f:            f.write(str(time.time()))
            f.write(str(time.time()))


# Run the application
if __name__ == "__main__": application
    # Initialize the applicationinitialize_app()
    initialize_app()
    lication
    # Run the Flask application    app.run(debug=True)


    app.run(debug=True)