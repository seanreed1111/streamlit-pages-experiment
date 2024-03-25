from pathlib import Path
import ast 
import os
import json
from functools import partial

import streamlit as st
import pandas as pd

from langchain_community.utilities.sql_database import SQLDatabase
import urllib
from langchain.schema import ChatMessage
from loguru import logger

LANGCHAIN_PROJECT = "Connect With SQL To DB - multipage app"
st.set_page_config(page_title=LANGCHAIN_PROJECT, page_icon="")
st.markdown(f"### {LANGCHAIN_PROJECT}")
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

MAX_TOKENS = 1000
SCHEMA = {"schema":"sandbox"}
CONFIG_DIR_PATH = st.session_state["config_dir_path"]

@logger.catch
@st.cache_resource(ttl="4h")
def get_db_engine(db_config_file="dbconfig.json", config_dir_path = CONFIG_DIR_PATH, **kwargs):
    
    if not kwargs: 
        kwargs = {"schema":"sandbox"}
    
    @st.cache_resource(ttl="4h")    
    def get_wab_connection_string(db_config_file=db_config_file, config_dir_path=CONFIG_DIR_PATH ):
        driver= '{ODBC Driver 18 for SQL Server}'
        db_config_path = config_dir_path / db_config_file

        with open(db_config_path) as json_file:
            dbconfig = json.load(json_file)

        server = dbconfig['server']
        database = dbconfig['database']
        uid = dbconfig['username']
        pwd = dbconfig['password']
        port = int(dbconfig.get("port",1433))
        pyodbc_connection_string = f"DRIVER={driver};SERVER={server};PORT={port};DATABASE={database};UID={uid};PWD={pwd};Encrypt=yes;Connection Timeout=30;READONLY=True;"
        params = urllib.parse.quote_plus(pyodbc_connection_string)
        sqlalchemy_connection_string = f"mssql+pyodbc:///?odbc_connect={params}"
        return sqlalchemy_connection_string
    

    return SQLDatabase.from_uri(database_uri=get_wab_connection_string(),
                                **kwargs
                               )

test_query = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'trg'
    ORDER BY TABLE_NAME;
    """  

with st.sidebar:
    st.spinner("connecting to database..")
    try: 
        db = get_db_engine(**SCHEMA)

        db.run(test_query)
        st.success("Sucessfully connected to the database")
    except Exception as e:
        st.error(e)
        logger.error(str(e))


@logger.catch
@st.cache_data
def parse_repsonse(response: str):
    python_obj_from_response = ast.literal_eval(response)
    logger.info(f"python_obj_from_response = {python_obj_from_response}")
    if isinstance(python_obj_from_response, list):
        return ("ok", python_obj_from_response)
    return ("error", response)


@st.cache_data
def get_dataframe_from_response(response):
    logger.info(f"response = {response}")
    status_code, parsed_response = parse_repsonse(response)
    if status_code == "ok":
        df = pd.DataFrame(parsed_response)
        if df is not None:
            return ("ok", df)

    return ("error", response)

# def reset_chat():
#     st.session_state["sql_messages"] = []

reset_chat_button = st.button("Reset Chat") 

if "sql_messages" not in st.session_state or reset_chat_button or not st.session_state["sql_messages"]:
    first_sql_message = ChatMessage(role="assistant", content="Enter your MSSQL Query to run against the db")
    st.session_state["sql_messages"] = [first_sql_message]
    st.session_state["first_sql_message"] = first_sql_message

for msg in st.session_state.sql_messages:
    if msg.role == "user":
        st.chat_message(msg.role).write(msg.content)
    elif msg.role == "assistant" and msg != st.session_state["first_sql_message"]:
        status_code, repsonse = get_dataframe_from_response(msg.content) #msg.content is always text
        st.chat_message(msg.role).write(repsonse)       


with st.sidebar:
    st.sidebar.write("here is a sample query: ")
    st.sidebar.write(test_query)

if prompt := st.chat_input():
    with st.spinner("running query"):
        st.session_state.sql_messages.append(ChatMessage(role="user", content=prompt))
        try:
            response = db.run(prompt)

        except Exception as e:
            response = str(e)

    with st.chat_message("assistant"):
        st.session_state.sql_messages.append(ChatMessage(role="assistant", content=response))
