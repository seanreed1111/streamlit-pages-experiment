# reference docs https://python.langchain.com/docs/integrations/toolkits/sql_database#use-sqldatabasetoolkit-within-an-agenthttps://python.langchain.com/docs/expression_language/cookbook/sql_db

#https://python.langchain.com/docs/expression_language/cookbook/sql_db
import streamlit as st
from pathlib import Path
import os
import json
# from langchain_community.chat_models.azure_openai import AzureChatOpenAI #deprecated class, fix later
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_sql_agent
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
# from langchain.callbacks import StreamlitCallbackHandler
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain.schema import ChatMessage
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from loguru import logger
# import sqlalchemy
# from sqlalchemy import create_engine
import urllib

LANGCHAIN_PROJECT = f"Multipage App #2 Chat With SQL Agent WAB DB"
st.set_page_config(page_title=LANGCHAIN_PROJECT, page_icon="")
st.markdown(f"### {LANGCHAIN_PROJECT}")

with st.sidebar:
    llm_choice_radio = st.radio("Choose one", ["GPT-3.5-turbo", "GPT-4-turbo"])
    if llm_choice_radio == "GPT-3.5-turbo":
        st.session_state["agent_model_name"] = os.getenv("MODEL_NAME_GPT35")
        st.session_state["agent_deployment_name"] = os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME_GPT35")
    elif llm_choice_radio == "GPT-4-turbo":
        st.session_state["agent_model_name"] = os.getenv("MODEL_NAME")     
        st.session_state["agent_deployment_name"] = os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME")
    st.info(f"Now using {llm_choice_radio} as the underlying agent llm.")

os.environ["LANGCHAIN_PROJECT"] = f"{LANGCHAIN_PROJECT} with {llm_choice_radio}"

with st.spinner("Setting up agent...please wait"):
    CONFIG_DIR_PATH = st.session_state["config_dir_path"]
    try:
        db = st.session_state["db"]
    except:
        st.error("Please go back to main app page and connect to the WAB database")
        st.stop()

    llm = AzureChatOpenAI(
                temperature=0.1,
                streaming=True,
                # max_tokens=st.session_state["max_tokens"],
                azure_deployment=st.session_state["agent_deployment_name"],
                azure_endpoint=os.environ["AZURE_OPENAI_API_ENDPOINT"],
                model_name=st.session_state["agent_model_name"],
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                request_timeout=120,
                verbose=False
            )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    agent_executor = create_sql_agent(
        llm=llm,

        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        agent_executor_kwargs={"return_intermediate_steps":True, 
        "max_iterations":10}
    )
    st.success("Agent setup done!")

if "llm_sql_agent_messages" not in st.session_state or st.button("Clear message history") or not st.session_state.llm_sql_agent_messages:
    st.session_state["llm_sql_agent_messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.llm_sql_agent_messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.llm_sql_agent_messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        st_cb = StreamlitCallbackHandler(st.container())
        response = agent_executor.invoke({"input":prompt}, callbacks=[st_cb])
        st.session_state.llm_sql_agent_messages.append({"role": "assistant", "content": response})
        st.write(response)
