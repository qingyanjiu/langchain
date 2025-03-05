# https://python.langchain.com/docs/tutorials/sql_qa/
# pip install --upgrade --quiet langchain-community langchainhub langgraph

from langchain_community.utilities import SQLDatabase

db = SQLDatabase.from_uri("sqlite:///db_charts/Chinook.db")
# print(db.dialect)
# print(db.get_usable_table_names())
# res = db.run("SELECT * FROM Artist LIMIT 10;")



from langchain_ollama import ChatOllama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

# 本地模型，效果很差

# llm = ChatOllama(
#     base_url='http://localhost:11434',
#     model="llama3.2:3b",
#     temperature=0.7,
#     callback_manager=callback_manager
# )

# vllm
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url='https://shannon1997-a0m85kaya8fn-8000.gear-c1.openbayes.net/v1/',
    model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    temperature=0.7,
    callback_manager=callback_manager,
    api_key='123'
)

# 千问max
# OPENAI_API_KEY = 'sk-8e793baf80dd423e92386c2486209666'

# llm = ChatOpenAI(model='qwen-max',
#             api_key=OPENAI_API_KEY,
#             base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
#             temperature=0.7, 
#             callback_manager=callback_manager)

# response = llm.invoke("你好，你是谁？")
# print(response.content)

# exit(0)

from langchain_community.agent_toolkits import SQLDatabaseToolkit

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()

tools


# 拉取prompt，可以拉取后拿到prompt的messages手动拼装

# export LANGSMITH_API_KEY="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"

# if not os.environ.get("LANGSMITH_API_KEY"):
#     os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
#     os.environ["LANGSMITH_TRACING"] = "true"

# from langchain import hub

# prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

# assert len(prompt_template.messages) == 1




from langchain.prompts import SystemMessagePromptTemplate

template  = '''
System: You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.
'''

# 测试打印
system_message_prompt = SystemMessagePromptTemplate.from_template(template)

system_message = system_message_prompt.format(dialect="SQLite", top_k=5)


from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

agent_executor = create_react_agent(llm, tools, prompt=system_message)


question = "哪个国家的客户消费最高?"

for step in agent_executor.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()