"""Choose explicit Azure Blob credentials; never silently fall back to SAS."""
import os
from azure.storage.blob import ContainerClient

def client_from_url(url, factory=None):
    mode=os.environ.get("BTC_AZURE_AUTH","sas").lower()
    constructor=factory or ContainerClient.from_container_url
    if mode=="sas":
        return constructor(url)
    if mode=="oidc":
        from azure.identity import AzureCliCredential
        return constructor(url,credential=AzureCliCredential())
    raise ValueError("BTC_AZURE_AUTH must be 'sas' or 'oidc'")

def storage_url():
    mode=os.environ.get("BTC_AZURE_AUTH","sas").lower()
    if mode=="oidc":
        return "https://btcquantlabstorage.blob.core.windows.net/btc-historical-data"
    if mode=="sas":
        value=os.environ.get("AZURE_BLOB_CONTAINER_SAS_URL")
        if not value:
            raise ValueError("Missing AZURE_BLOB_CONTAINER_SAS_URL")
        return value
    raise ValueError("Unrecognized authentication mode")
