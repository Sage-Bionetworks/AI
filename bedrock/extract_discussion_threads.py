import synapseclient
from typing import Iterator
import requests


def get_project_forum(syn, projectid: str) -> dict:
    """Get the Forum's metadata for a given project ID.
    https://rest-docs.synapse.org/rest/GET/project/projectId/forum.html
    """
    return syn.restGET(f"/project/{projectid}/forum")


def get_forum(syn, forumid: str) -> dict:
    """Get the Forum's metadata for a given forum ID.
    https://rest-docs.synapse.org/rest/GET/forum/forumId.html
    """
    return syn.restGET(f"/forum/{forumid}")


def get_forum_threads(
    syn, forumid: str, query_filter: str = "EXCLUDE_DELETED", **kwargs
) -> Iterator[dict]:
    """Get N number of threads for a given forum ID
    https://rest-docs.synapse.org/rest/GET/forum/forumId/threads.html

    Args:

        forumid: Forum ID
        query_filter:  filter forum threads returned. Can be NO_FILTER,
                    DELETED_ONLY, EXCLUDE_DELETED.
                    Defaults to EXCLUDE_DELETED.

    Yields:
        list: Forum threads

    """
    uri = f"/forum/{forumid}/threads?filter={query_filter}"
    threads = syn._GET_paginated(uri, **kwargs)
    for thread in threads:
        yield thread


def get_thread(syn, threadid: str) -> dict:
    """Get a thread and its statistic given its ID
    https://rest-docs.synapse.org/rest/GET/thread/threadId.html
    """
    return syn.restGET(f"/thread/{threadid}")


def get_thread_replies(
    syn, threadid: str, query_filter: str = "EXCLUDE_DELETED", **kwargs
) -> Iterator[dict]:
    """Get N number of replies for a given thread ID
    https://rest-docs.synapse.org/rest/GET/thread/threadId/replies.html

    Args:
        threadid: Forum thread id
        query_filter:  filter forum thread replies returned.
                        Can be NO_FILTER, DELETED_ONLY, EXCLUDE_DELETED.
                        Defaults to EXCLUDE_DELETED.
    Yields:
        list: Forum threads replies
    """
    replies = syn._GET_paginated(
        f"/thread/{threadid}/replies?filter={query_filter}", **kwargs
    )
    for reply in replies:
        yield reply


def _get_text(url: str):
    """
    Get the text from a message url

    Args:
        url: rest call URL

    Returns:
        response: Request response
    """
    response = requests.get(url["messageUrl"].split("?")[0])
    return response


def _get_message_url(syn, messagekey: str, thread_or_reply: str) -> dict:
    """message URL of a thread. The message URL is the URL
    to download the file which contains the thread message.
    https://rest-docs.synapse.org/rest/GET/thread/messageUrl.html
    """
    return syn.restGET(f"/{thread_or_reply}/messageUrl?messageKey={messagekey}")


def get_text(syn, messagekey: str, thread_or_reply: str):
    """
    Get the text from a message url

    Args:
        url: rest call URL

    Returns:
        response: Request response
    """
    url = _get_message_url(syn, messagekey, thread_or_reply)
    response = _get_text(url)
    return response.text


def main():
    syn = synapseclient.login()
    project_forum = get_project_forum(syn, "syn7222066")
    forum = get_forum(syn, project_forum["id"])
    for thread in get_forum_threads(syn, forum["id"]):
        # url = _get_message_url(syn, thread['messageKey'], 'thread')
        # response = _get_text(url)
        text = get_text(syn, thread["messageKey"], "thread")
        with open(f"{thread['id']}.txt", "w") as thread_f:

            author = syn.getUserProfile(thread["createdBy"]).userName
            thread_f.write(f"Thread: {author}")
            thread_f.write("\n")
            thread_f.write(text)
            thread_f.write("\n")

            for reply in get_thread_replies(syn, thread["id"]):
                # url = _get_message_url(syn, reply['messageKey'], 'reply')
                # response = _get_text(url)
                text = get_text(syn, reply["messageKey"], "reply")
                reply_author = syn.getUserProfile(reply["createdBy"]).userName
                thread_f.write(f"Reply: {reply_author}")
                thread_f.write("\n")
                thread_f.write(text)
                thread_f.write("\n")


if __name__ == "__main__":
    main()
