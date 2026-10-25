import json
import hashlib
import pytest
from src.upload_azure import upload

class FakeClient:
    def __init__(self): self.names=[]
    def upload_blob(self,name,data,overwrite):
        assert data.read() and overwrite
        self.names.append(name)

def make(tmp_path,first=0,last=60):
    sample=b'parquet fixture'
    filename=f'BTCUSD_1m_{first}_{last}.parquet'
    (tmp_path/filename).write_bytes(sample)
    (tmp_path/'BTCUSD_1m_manifest.json').write_text(json.dumps([{
        'filename':filename,'start':first,'end_exclusive':last,
        'sha256':hashlib.sha256(sample).hexdigest()}]))
    return filename

def test_unique_cloud_manifest(tmp_path):
    file=make(tmp_path)
    client=FakeClient()
    names=upload(tmp_path,'https://example.invalid/container?sv=mock',client_factory=lambda _:client)
    assert names==client.names
    assert names==['historical/BTCUSD/1m/'+file,'historical/BTCUSD/1m/manifests/BTCUSD_1m_0_60.json']

def test_reject_tampered_partition(tmp_path):
    file=make(tmp_path)
    (tmp_path/file).write_bytes(b'tampered')
    with pytest.raises(ValueError,match='checksum'):
        upload(tmp_path,'mock',client_factory=lambda _:FakeClient())
