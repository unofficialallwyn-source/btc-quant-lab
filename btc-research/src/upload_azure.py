"""Optional durable storage of verified partitions to a private Azure Blob container."""
import argparse
import json
import os
from pathlib import Path

def upload(directory, container_url, prefix="historical/BTCUSD/1m", client_factory=None):
    from azure.storage.blob import ContainerClient
    path = Path(directory)
    manifests = sorted(path.glob("BTCUSD_1m_manifest.json"))
    if len(manifests) != 1:
        raise ValueError("Exactly one manifest is required")
    records = json.loads(manifests[0].read_text())
    if not records:
        raise ValueError("Empty manifest")
    for item in records:
        if Path(item["filename"]).name != item["filename"]:
            raise ValueError("Unsafe manifest filename")
        if not (path/item["filename"]).is_file():
            raise ValueError("Missing referenced partition")
    client = (client_factory or ContainerClient.from_container_url)(container_url)
    uploaded = []
    # Upload parquet before manifest so manifest indicates completed batch.
    for filename in [x["filename"] for x in records] + [manifests[0].name]:
        name = f"{prefix.strip('/')}/{filename}"
        with (path/filename).open("rb") as f:
            client.upload_blob(name=name, data=f, overwrite=True)
        uploaded.append(name)
    return uploaded

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--directory",required=True)
    ap.add_argument("--prefix",default="historical/BTCUSD/1m")
    args=ap.parse_args()
    url=os.environ.get("AZURE_BLOB_CONTAINER_SAS_URL")
    if not url:
        raise SystemExit("AZURE_BLOB_CONTAINER_SAS_URL is required for durable storage")
    names=upload(args.directory,url,args.prefix)
    print(f"Uploaded {len(names)} Azure blobs")

if __name__=="__main__": main()
