import json
import hashlib
from src.upload_azure import upload

class FakeClient:
    def __init__(self): self.names=[]
    def upload_blob(self, name, data, overwrite):
        assert data.read()
        assert overwrite is True
        self.names.append(name)

def test_azure_upload_mock(tmp_path):
    sample=b"sample parquet placeholder"
    (tmp_path/"BTCUSD_1m_0_60.parquet").write_bytes(sample)
    (tmp_path/"BTCUSD_1m_manifest.json").write_text(json.dumps([
        {"filename":"BTCUSD_1m_0_60.parquet", "sha256":hashlib.sha256(sample).hexdigest()}
    ]))
    fake=FakeClient()
    result=upload(tmp_path,"https://example.invalid/container?sv=mock",client_factory=lambda _:fake)
    assert len(result)==2
    assert result==fake.names
