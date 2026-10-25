"""Upload BTC partitions with distinct run manifests for safe cross-run retention."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def upload(directory, container_url, prefix="historical/BTCUSD/1m", client_factory=None):
    from azure.storage.blob import ContainerClient
    path=Path(directory)
    manifest=path/"BTCUSD_1m_manifest.json"
    records=json.loads(manifest.read_text())
    if not records: raise ValueError("Empty manifest")
    start=records[0]["start"]
    end=records[-1]["end_exclusive"]
    for i,item in enumerate(records):
        filename=item["filename"]
        if not isinstance(filename,str) or Path(filename).name!=filename:
            raise ValueError("Unsafe partition filename")
        source=path/filename
        if not source.is_file(): raise ValueError("Missing referenced partition")
        if hashlib.sha256(source.read_bytes()).hexdigest()!=item["sha256"]:
            raise ValueError("Partition checksum mismatch")
        if i and records[i-1]["end_exclusive"] != item["start"]:
            raise ValueError("Noncontiguous partition windows")
    client=(client_factory or ContainerClient.from_container_url)(container_url)
    destination=prefix.strip("/")
    completed=[]
    for item in records:
        name=f'{destination}/{item["filename"]}'
        with (path/item["filename"]).open("rb") as f:
            client.upload_blob(name=name,data=f,overwrite=True)
        completed.append(name)
    # The manifest is published last, with a unique name per UTC coverage range.
    name=f"{destination}/manifests/BTCUSD_1m_{start}_{end}.json"
    with manifest.open("rb") as f:
        client.upload_blob(name=name,data=f,overwrite=True)
    completed.append(name)
    return completed

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--directory",required=True)
    ap.add_argument("--prefix",default="historical/BTCUSD/1m")
    a=ap.parse_args()
    url=os.environ.get("AZURE_BLOB_CONTAINER_SAS_URL")
    if not url: raise SystemExit("Missing AZURE_BLOB_CONTAINER_SAS_URL")
    names=upload(a.directory,url,a.prefix)
    print(f"Uploaded {len(names)} Azure blobs; manifest last: {names[-1]}")

if __name__=="__main__":
    main()
