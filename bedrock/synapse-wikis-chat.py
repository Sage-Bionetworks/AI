import json
import uuid

import boto3
from botocore.exceptions import ClientError
import streamlit as st


def invoke_agent(agents_runtime_client, agent_id, agent_alias_id, session_id, prompt):
    """
    Sends a prompt for the agent to process and respond to.

    Args:
        agent_id: The unique identifier of the agent to use.
        agent_alias_id: The alias of the agent to use.
        session_id: The unique identifier of the session. Use the same value across requests
                    to continue the same conversation.
        prompt: The prompt that you want Claude to complete.

    Returns:
        Inference response from the model.
    """

    try:
        response = agents_runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=prompt,
        )

        completion = ""

        for event in response.get("completion"):
            chunk = event["chunk"]
            completion = completion + chunk["bytes"].decode()

    except ClientError as e:
        print(f"Couldn't invoke agent. {e}")
        raise

    return completion


st.title("Explore Synapse")
with st.chat_message("user"):
    st.write("Hello 👋, finding a dataset for your research?")

runtime_client = boto3.client(
    service_name="bedrock-agent-runtime", region_name="us-east-1"
)
prompt = st.chat_input("Say something")
if prompt:
    st.write(f"You asked: {prompt}")
    with st.spinner("Wait for it..."):
        response = invoke_agent(
            agents_runtime_client=runtime_client,
            agent_id="JMQZXOQVRB",
            agent_alias_id="1EY4IHHBXR",
            session_id=str(uuid.uuid1()),
            prompt=prompt,
        )
    st.write(f"Answer: {response}")
