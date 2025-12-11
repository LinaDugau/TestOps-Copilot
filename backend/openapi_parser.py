from prance import ResolvingParser

def load_openapi_spec(path: str) -> dict:
    parser = ResolvingParser(path, backend="openapi-spec-validator")
    return parser.specification


def extract_endpoints(spec: dict):
    endpoints = []

    for path, methods in spec.get("paths", {}).items():
        for method, info in methods.items():
            ep = {
                "path": path,
                "method": method.upper(),
                "summary": info.get("summary", ""),
                "parameters": info.get("parameters", []),
                "requestBody": info.get("requestBody", {}),
                "responses": info.get("responses", {})
            }
            endpoints.append(ep)

    return endpoints

def extract_negative_responses(ep):
    return {
        code: info
        for code, info in ep["responses"].items()
        if str(code).startswith(("4", "5"))
    }