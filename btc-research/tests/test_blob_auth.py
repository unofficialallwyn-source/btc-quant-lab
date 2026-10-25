import pytest
from src.blob_auth import client_from_url, storage_url

def test_legacy_sas_selected(monkeypatch):
    monkeypatch.setenv('BTC_AZURE_AUTH','sas')
    monkeypatch.setenv('AZURE_BLOB_CONTAINER_SAS_URL','https://example.invalid/backup?sig=abc')
    assert storage_url().endswith('sig=abc')
    assert client_from_url('sas-url',lambda url:('sas',url))==('sas','sas-url')

def test_oidc_client_selected(monkeypatch):
    monkeypatch.setenv('BTC_AZURE_AUTH','oidc')
    assert storage_url()=='https://btcquantlabstorage.blob.core.windows.net/btc-historical-data'
    def fake(url,**kwargs):
        assert 'credential' in kwargs
        return ('oidc',url)
    assert client_from_url(storage_url(),fake)[0]=='oidc'

def test_no_implicit_fallback(monkeypatch):
    monkeypatch.setenv('BTC_AZURE_AUTH','unknown')
    with pytest.raises(ValueError):
        storage_url()
