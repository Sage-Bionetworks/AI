import os

import autogen
from dotenv import load_dotenv

# Load Together AI environmental var
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

# # Setting up the agents

llm_config = {
    "cache_seed": 41,  # seed for caching and reproducibility
    "config_list": config_list,  # a list of OpenAI API configurations
    "temperature": 0,  # temperature for sampling
}

# TODO: Comment out docker executor first because we may need to install pandas...
# with autogen.coding.DockerCommandLineCodeExecutor(work_dir="coding") as code_executor:

# create a UserProxyAgent instance named "user_proxy"
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "last_n_messages": 3,
        "work_dir": "coding",
        "use_docker": False,
    },
    system_message="A human admin."
)

coder = autogen.AssistantAgent(
    name="Coder",
    llm_config=llm_config,
)

critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""
Critic. You are a helpful assistant highly skilled in evaluating the quality of a given data mapping and processing code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER DATA PROCESSING BEST PRACTICES for each evaluation.  You can infer the data type from the filename. Specifically, you can carefully evaluate the code across the following dimensions
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the columns? E.g., are the values standardized?
- Goal compliance (compliance): how well the code meets the specified goals?
- Data encoding (encoding): Is the data encoded appropriately for the visualization type?

YOU MUST PROVIDE A SCORE for each of the above dimensions.
{bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
Do not suggest code.
Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.
""",
    llm_config=llm_config,
)

# TODO: this is sub optimal, because it doesn't quit out after a successful execution
def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    rounds = len(messages) // 2  # Each round consists of a coder and a user_proxy message

    if not messages:
        # If there are no messages yet, start with coder
        return coder
    elif last_speaker is coder:
        # coder -> user_proxy
        return critic
    elif last_speaker is user_proxy:
        # user_proxy -> coder
        return coder
    elif last_speaker is critic:
        # critic -> end or coder
        if rounds >= groupchat.max_round:
            return None
        return coder

groupchat = autogen.GroupChat(
    agents=[user_proxy, coder, critic],
    messages=[],
    max_round=20,
    speaker_selection_method=state_transition,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

def my_message_generator(sender, recipient, context):
    # your CSV file
    file_name = context.get("file_name")
    try:
        with open(file_name, mode="r", encoding="utf-8") as file:
            file_content = file.read()
    except FileNotFoundError:
        file_content = "No data found."
    return "Filling in the null, nan, empty, N/A or None from the provided data. YOU MUST SAVE THE FINAL DATA TO A CSV. \nData:\n" + file_content


user_proxy.initiate_chat(
    manager,
    message=my_message_generator,
    file_name="coding/genie_portal.csv",
    initial_agent=coder
    # summary_method="reflection_with_llm",
)
