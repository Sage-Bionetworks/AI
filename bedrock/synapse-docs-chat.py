import boto3

import streamlit as st


def get_answers(questions):
    """
    This function takes a string of questions and asks the Anthropic AI to generate answers
    based on the knowledge base of Synapse documentation.

    Args:
        questions (str): A string of user questions.

    Returns:
        knowledgeBaseResponse (dict): A dictionary containing the generated answers.
    """
    bedrock_client = boto3.client("bedrock-agent-runtime", "us-east-1")

    knowledge_base_response = bedrock_client.retrieve_and_generate(
        input={"text": questions},
        retrieveAndGenerateConfiguration={
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": "8MYDVVSHMT",
                "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
            },
            "type": "KNOWLEDGE_BASE",
        },
    )
    # context = response['citations'][0]['retrievedReferences'][0]['content']['text']
    # doc_url = response['citations'][0]['retrievedReferences'][0]['location']['s3Location']['uri']
    instructions_list = [
        i["generatedResponsePart"]["textResponsePart"]["text"]
        for i in knowledge_base_response["citations"]
    ]

    return "\n".join(instructions_list)


st.title("Get Synapse Help")
with st.chat_message("user"):
    st.write("Hello 👋, do you need Synapse help?")

prompt = st.chat_input("Say something")
if prompt:
    st.write(f"You asked: {prompt}")
    with st.spinner("Wait for it..."):
        answer = get_answers(prompt)
    st.write(f"Answer: {answer}")
