"""Read externally sourced Delta research inputs from private Azure Blob prefix.

Uses existing Azure OIDC read access; no secrets or invented observations.
"""
import argparse
from pathlib import Path
from .blob_auth import client_from_url,storage_url


def download(prefix,dest):
    if not prefix or prefix.startswith("/") or ".." in prefix.split("/"):
        raise ValueError("Provide a safe, relative Azure Blob prefix")
    client=client_from_url(storage_url())
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    for file in ("source_manifest.json","mark_1m.csv","fx_1m.csv","funding_8h.csv"):
        blob=client.get_blob_client(prefix.rstrip("/")+"/"+file)
        (dest/file).write_bytes(blob.download_blob().readall())
    return dest


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prefix",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    download(a.prefix,a.output)


if __name__=="__main__":
    main()
