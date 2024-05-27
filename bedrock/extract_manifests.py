"""Download HTAN manifests from Synapse
Execute 5/25/2024"""

import shutil

import synapseclient


def main():
    syn = synapseclient.login()

    manifest = syn.tableQuery(
        "SELECT id FROM syn20446927 where name like '%manifest%' and type = 'file'"
    )
    manifest_df = manifest.asDataFrame()

    for i in manifest_df["id"]:
        if i == "syn35565633":
            continue
        print(i)
        ent = syn.get(i)
        shutil.copy(ent.path, f"{ent.id}-{ent.name}")


if __name__ == "__main__":
    main()
