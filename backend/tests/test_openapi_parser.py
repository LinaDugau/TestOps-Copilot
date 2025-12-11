import pytest
from backend.openapi_parser import load_openapi_spec, extract_endpoints, extract_negative_responses

def test_extract_endpoints_basic():
    spec = {
        "paths": {
            "/vms": {
                "get": {
                    "summary": "List VMs",
                    "parameters": [],
                    "requestBody": {},
                    "responses": {"200": {}, "400": {}}
                }
            }
        }
    }

    eps = extract_endpoints(spec)
    assert len(eps) == 1
    ep = eps[0]
    assert ep["path"] == "/vms"
    assert ep["method"] == "GET"

def test_extract_negative_responses():
    ep = {"responses": {"200": {}, "400": {}, "500": {}}}
    neg = extract_negative_responses(ep)
    assert "400" in neg
    assert "500" in neg
    assert "200" not in neg


def test_load_openapi_spec_mocked(monkeypatch):
    class DummyParser:
        def __init__(self, *args, **kwargs):
            self.specification = {"paths": {}}

    monkeypatch.setattr("backend.openapi_parser.ResolvingParser", DummyParser)

    spec = load_openapi_spec("fake.yaml")
    assert spec == {"paths": {}}