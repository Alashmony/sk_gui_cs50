# import json
import inspect
import sqlite3
import os
import pandas as pd
import numpy as np
import io
import base64
import matplotlib.pyplot as plt
from datetime import datetime


def get_methods(object):
    """Gets all methods for a certain type, returns a dictionary of methods and their description

    Args:
        object (_type_): _description_
    """
    methodList = []
    spacing = 0
    methods = {}
    for method_name in dir(object):
        try:
            if callable(getattr(object, method_name)):
                methodList.append(str(method_name))
                spacing = max(spacing, len(method_name))
        except Exception:
            methodList.append(str(method_name))
    # processFunc = (lambda s: " ".join(s.split())) or (lambda s: s)
    for method in methodList:
        try:
            m_desc = getattr(object, method).__doc__
            m_args = list(inspect.signature(getattr(object, method)).parameters.keys())

            # print(str(method.ljust(spacing)) + " " + m_desc)
            if m_desc is not None and m_desc != "None" and not method.startswith("_"):
                methods[method] = {}
                methods[method]["args"] = m_args
                methods[method]["description"] = m_desc
        except Exception as e:
            print(method.ljust(spacing) + " " + str(e) + " failed")
    return methods


def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('sk_gui.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create projects table
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        uuid TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create dataframes table to track multiple dataframes in a project
    c.execute('''
    CREATE TABLE IF NOT EXISTS dataframes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        data_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    ''')
    
    # Create steps table to track transformation steps
    c.execute('''
    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataframe_id INTEGER NOT NULL,
        step_number INTEGER NOT NULL,
        step_code TEXT NOT NULL,
        dataframe_version TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dataframe_id) REFERENCES dataframes (id)
    )
    ''')
    
    conn.commit()
    conn.close()


def get_db_connection():
    """Get a connection to the database"""
    conn = sqlite3.connect('sk_gui.db')
    conn.row_factory = sqlite3.Row
    return conn


def generate_plot(df, x_column, y_column, plot_type='line', title=''):
    """Generate a plot using matplotlib and return as base64 encoded string"""
    plt.figure(figsize=(10, 6))
    
    if plot_type == 'line':
        plt.plot(df[x_column], df[y_column])
    elif plot_type == 'scatter':
        plt.scatter(df[x_column], df[y_column])
    elif plot_type == 'bar':
        plt.bar(df[x_column], df[y_column])
    elif plot_type == 'hist':
        plt.hist(df[y_column], bins=20)
    elif plot_type == 'box':
        df.boxplot(column=[y_column])
    
    plt.title(title)
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.tight_layout()
    
    # Save plot to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Encode the plot as base64
    plot_data = base64.b64encode(buf.getbuffer()).decode('ascii')
    return f"data:image/png;base64,{plot_data}"


def perform_series_operation(series, operation, **kwargs):
    """Perform operations on pandas Series"""
    if operation == 'describe':
        return series.describe()
    elif operation == 'value_counts':
        return series.value_counts()
    elif operation == 'unique':
        return pd.Series(series.unique())
    elif operation == 'fill_na':
        return series.fillna(kwargs.get('value', 0))
    elif operation == 'replace':
        return series.replace(kwargs.get('to_replace'), kwargs.get('value'))
    elif operation == 'map':
        return series.map(eval(kwargs.get('function')))
    elif operation == 'apply':
        return series.apply(eval(kwargs.get('function')))
    elif operation == 'astype':
        return series.astype(kwargs.get('dtype'))
    else:
        raise ValueError(f"Operation '{operation}' not supported")
