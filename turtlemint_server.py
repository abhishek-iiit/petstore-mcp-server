from mcp.server.fastmcp import FastMCP
import requests
import json
import inspect
import hashlib
import re

# CHANGE THESE TO YOUR TARGET API!
BASE_URL = "https://app.turtlemint.com"
OPENAPI_URL = "https://app.turtlemint.com/api/docs/swagger-ui-init.js"

mcp = FastMCP(
    name="TurtlemintAPI",
    description="Interact with the Turtlemint API dynamically.",
    instructions="Use these tools to query and update resources in the Turtlemint API. All endpoints are available."
)

def sanitize_name(name: str) -> str:
    return name.replace("-", "_")

def unsanitize_name(name: str) -> str:
    return name.replace("_", "-")

def make_api_request(method, endpoint, data=None, params=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    final_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        final_headers.update(headers)

    try:
        if method.lower() == "get":
            response = requests.get(url, params=params, headers=final_headers)
        elif method.lower() == "post":
            response = requests.post(url, json=data, params=params, headers=final_headers)
        elif method.lower() == "put":
            response = requests.put(url, json=data, params=params, headers=final_headers)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=final_headers, params=params)
        else:
            return {"error": "Invalid HTTP method"}
        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def format_api_response(response):
    if isinstance(response, dict) and "error" in response:
        return f"Error: {response['error']}\n\nDetails: {response.get('details', 'No additional details')}"
    return json.dumps(response, indent=2)

def extract_swagger_doc_from_js(js_code: str):
    key = 'swaggerDoc'
    start_idx = js_code.find(key)
    if start_idx == -1:
        raise ValueError("No 'swaggerDoc' found in JS content")

    brace_start = js_code.find('{', start_idx)
    if brace_start == -1:
        raise ValueError("Opening brace for swaggerDoc not found")

    count = 0
    for i in range(brace_start, len(js_code)):
        if js_code[i] == '{':
            count += 1
        elif js_code[i] == '}':
            count -= 1
            if count == 0:
                json_str = js_code[brace_start:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse swaggerDoc JSON: {e}")
    raise ValueError("Unmatched braces while parsing swaggerDoc")

def get_openapi_spec():
    try:
        resp = requests.get(OPENAPI_URL)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()
        if "application/javascript" in content_type:
            return extract_swagger_doc_from_js(resp.text)
        elif "application/json" in content_type:
            return resp.json()
        else:
            raise ValueError(f"Unsupported content-type: {content_type}")

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch OpenAPI spec: {e}") from e

def parse_parameters(parameters):
    args = []
    defaults = {}
    for param in parameters:
        name = sanitize_name(param["name"])
        required = param.get("required", False)
        param_type = param.get("type") or (param.get("schema") or {}).get("type", "str")
        if not required:
            defaults[name] = None
        args.append(name)
    return args, defaults

def build_func(endpoint, method, operation):
    parameters = operation.get("parameters", [])
    request_body = operation.get("requestBody")
    if request_body:
        content = request_body.get("content", {})
        if "application/json" in content:
            args, defaults = parse_parameters(parameters)
            args.append("body")
            defaults["body"] = None
        else:
            args, defaults = parse_parameters(parameters)
    else:
        args, defaults = parse_parameters(parameters)

    summary = operation.get("summary", f"{method.upper()} {endpoint}")

    def api_tool(**kwargs):
        path_params = {}
        query_params = {}
        headers = {}
        body = None

        for param in parameters:
            raw_name = param["name"]
            param_location = param.get("in", "query")
            sanitized_name = sanitize_name(raw_name)
            value = kwargs.get(sanitized_name)
            if value is None:
                continue

            if param_location == "path":
                path_params[raw_name] = value
            elif param_location == "query":
                query_params[raw_name] = value
            elif param_location == "header":
                headers[raw_name] = value

        if request_body and "body" in kwargs:
            body = kwargs.get("body")

        path = endpoint
        for k, v in path_params.items():
            path = path.replace("{" + k + "}", str(v))

        return format_api_response(
            make_api_request(method, path, data=body, params=query_params, headers=headers)
        )

    required = [arg for arg in args if arg not in defaults]
    optional = [arg for arg in args if arg in defaults]

    sig_params = []
    for arg in required:
        sig_params.append(inspect.Parameter(arg, inspect.Parameter.POSITIONAL_OR_KEYWORD))
    for arg in optional:
        sig_params.append(inspect.Parameter(arg, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=defaults[arg]))

    api_tool.__signature__ = inspect.Signature(sig_params)
    api_tool.__doc__ = summary
    return api_tool

def register_all_tools():
    spec = get_openapi_spec()
    for endpoint, ops in spec["paths"].items():
        for method, operation in ops.items():
            summary = operation.get("summary", f"{method.upper()} {endpoint}")
            func = build_func(endpoint, method, operation)
            tool_name = sanitize_tool_name(method, endpoint)
            mcp.tool(description=summary, name=tool_name)(func)

def sanitize_tool_name(method: str, endpoint: str) -> str:
    # Build initial name
    raw_name = f"{method}_{endpoint.strip('/').replace('/', '_').replace('{','').replace('}','')}"
    # Keep only allowed characters: a-z, A-Z, 0-9, -, _
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', raw_name)
    # If it's too long, hash part of it
    if len(cleaned) > 64:
        hash_suffix = hashlib.md5(cleaned.encode()).hexdigest()[:8]
        cleaned = cleaned[:55] + "_" + hash_suffix
    return cleaned

register_all_tools()

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run())
