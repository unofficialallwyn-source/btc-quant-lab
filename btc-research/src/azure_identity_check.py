"""Read-only Azure Blob inventory check using GitHub OIDC Azure CLI login."""
import argparse
import json
from azure.identity import AzureCliCredential
from azure.storage.blob import ContainerClient

def inspect(account,container,prefix="historical/BTCUSD/1m/manifests/"):
    credential=AzureCliCredential()
    client=ContainerClient(account_url=f"https://{account}.blob.core.windows.net",
                           container_name=container,credential=credential)
    names=[blob.name for blob in client.list_blobs(name_starts_with=prefix)]
    return {"account":account,"container":container,
            "manifest_count":len(names),
            "sample_manifest_names":names[:3]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--account",default="btcquantlabstorage")
    p.add_argument("--container",default="btc-historical-data")
    args=p.parse_args()
    print(json.dumps(inspect(args.account,args.container),indent=2))

if __name__=="__main__":
    main()
