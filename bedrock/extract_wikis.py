import copy

import synapseclient
from synapseclient import Synapse
import pandas as pd
import json


def get_all_wiki_pages(syn: Synapse, project_id: str):
    """Get all wiki pages and add metadata.json"""
    project_ent = syn.get(project_id)
    try:
        headers = syn.getWikiHeaders(project_id)
    except synapseclient.core.exceptions.SynapseHTTPError as e:
        # Originally, I had extracted out blank wiki pages for the
        # projects that didn't have it, but I decided that we don't
        # actually need to do that.
        # with open(f'{project_id}.md', 'w') as f:
        #     f.write('No Wiki')
        # metadata = {
        #     "metadataAttributes": {
        #         "id": project_ent['id'],
        #         "createdOn": project_ent['createdOn'],
        #         "createdBy": project_ent['createdBy'],
        #         "parentWikiId": project_ent.get('parentWikiId'),
        #         "title": project_ent['name'],
        #         "ownerId": project_ent['id'],
        #         "projectName": project_ent['name'],
        #     }
        # }
        # # Exclude all annotations with more than one value for now.
        # to_pull_annotations = {
        #     key: value[0] if len(value) == 1 else value
        #     for key, value in project_ent.annotations.items()

        # }
        # metadata['metadataAttributes'].update(to_pull_annotations)
        # metadata_copy = copy.deepcopy(metadata['metadataAttributes'])
        # for key in metadata_copy.keys():
        #     if metadata['metadataAttributes'][key] is None or metadata['metadataAttributes'][key] == '':
        #         del metadata['metadataAttributes'][key]
        # with open(f'{project_id}.md.metadata.json', 'w') as f:
        #     json.dump(metadata, f)
        headers = []

    for header in headers:
        header_id = header["id"]
        temp = syn.getWiki(project_id, header_id)
        metadata = {
            "metadataAttributes": {
                "id": temp["id"],
                "createdOn": temp["createdOn"],
                "createdBy": temp["createdBy"],
                "parentWikiId": temp.get("parentWikiId"),
                "title": temp.get("title"),
                "ownerId": temp["ownerId"],
                "projectName": project_ent["name"],
            }
        }
        # Exclude all annotations with more than one value for now.
        to_pull_annotations = {
            key: value[0] if len(value) == 1 else value
            for key, value in project_ent.annotations.items()
        }
        metadata["metadataAttributes"].update(to_pull_annotations)
        metadata_copy = copy.deepcopy(metadata["metadataAttributes"])
        # bedrock does not play nicely with blank values in the metadata.json file
        for key in metadata_copy.keys():
            if (
                metadata["metadataAttributes"][key] is None
                or metadata["metadataAttributes"][key] == ""
                or metadata["metadataAttributes"][key] == []
            ):
                del metadata["metadataAttributes"][key]
        with open(f"{project_id}-{header_id}.md.metadata.json", "w") as f:
            json.dump(metadata, f)


def main():
    syn = synapseclient.login()
    # Extracted public projects from snowflake on 5/25/2024
    # select 'syn'||id as id from synapse_data_warehouse.synapse.node_latest where node_type = 'project' and is_public;
    projects = pd.read_csv("public_projects.csv")
    for project_id in projects["ID"]:
        print(project_id)
        get_all_wiki_pages(syn, project_id)


if __name__ == "__main__":
    main()
