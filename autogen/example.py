import os
from dotenv import load_dotenv
from pathlib import Path

import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor

load_dotenv()  

config_list = [
    {
        # Let's choose the Mixtral 8x7B model
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        # Provide your Together.AI API key here or put it into the TOGETHER_API_KEY environment variable.
        "api_key": os.environ.get("TOGETHER_API_KEY"),
        # We specify the API Type as 'together' so it uses the Together.AI client class
        "api_type": "together",
        "stream": False,
    }
]

# Setting up the code executor
# workdir = Path("coding")
# workdir.mkdir(exist_ok=True)
# code_executor = LocalCommandLineCodeExecutor(work_dir=workdir)

# # Setting up the agents

llm_config = {
    # "cache_seed": 40,  # seed for caching and reproducibility
    "config_list": config_list,  # a list of OpenAI API configurations
    "temperature": 0,  # temperature for sampling
}


system_message = """You are a helpful AI assistant who writes code and the user executes it.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) for the user to execute.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
IMPORTANT: Wait for the user to execute your code and then you can reply with the word "FINISH". DO NOT OUTPUT "FINISH" after your code block."""

# system_message = """
# You are a data curator who writes code to map values from one to another or fills in values manually by inferring it and the user executes it.
# Solve tasks using your coding and language skills.
# In the following cases, suggest python code (in a python coding block) for the user to execute.
# Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
# When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
# Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
# If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
# When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
# IMPORTANT: Wait for the user to execute your code and then you can reply with the word "FINISH". DO NOT OUTPUT "FINISH" after your code block."""
# create an AssistantAgent named "assistant"


with autogen.coding.DockerCommandLineCodeExecutor(work_dir="coding") as code_executor:

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config={
            # the executor to run the generated code
            "executor": code_executor,
        },
        system_message=system_message
    )

    def my_message_generator(sender, recipient, context):
        # your CSV file
        file_name = context.get("file_name")
        try:
            with open(file_name, mode="r", encoding="utf-8") as file:
                file_content = file.read()
        except FileNotFoundError:
            file_content = "No data found."
        return "Take the following csv and create a new one by filling in the null, nan, empty, or None values with information available to you about project GENIE.  You can infer the data type from the filename. \n Data: \n" + file_content


    initializer = autogen.UserProxyAgent(
        name="Init",
    )
    coder = autogen.AssistantAgent(
        name="Retrieve_Action_1",
        llm_config=llm_config,
        system_message="""
        You are the Coder. Given a csv, you will fill in all the null, nan, empty, or None values with information available to you.
        You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
        Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
        If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
        """,
    )
    data_curator = AssistantAgent(
        name="data_curator",
        llm_config=llm_config,
        system_message="""
        You are a data curator, please ensure that there are no typos. If there are any blank values, fill it in.  Standardize any values.
        """
    )

    def state_transition(last_speaker, groupchat):
        messages = groupchat.messages

        if last_speaker is initializer:
            # init -> retrieve
            return coder
        elif last_speaker is coder:
            # retrieve: action 1 -> action 2
            return user_proxy
        elif last_speaker is user_proxy:
            if messages[-1]["content"] == "exitcode: 1":
                # retrieve --(execution failed)--> retrieve
                return coder
            else:
                # retrieve --(execution success)--> research
                return data_curator
        elif last_speaker == "data_curator":
            # research -> end
            return None

    groupchat = autogen.GroupChat(
        agents=[initializer, coder, user_proxy, data_curator],
        messages=[],
        max_round=10,
        speaker_selection_method=state_transition,
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    initializer.initiate_chat(
        manager,
        message=my_message_generator,
        file_name="coding/genie_portal.csv",
    )