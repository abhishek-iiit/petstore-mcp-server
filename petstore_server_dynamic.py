from mcp.server.fastmcp import FastMCP
import requests
import json
import inspect

BASE_URL = "https://petstore.swagger.io/v2"
OPENAPI_URL = f"{BASE_URL}/swagger.json"

mcp = FastMCP(
    name="PetstoreAPI",
    description="Interact with the Petstore Swagger API dynamically.",
    instructions="Use these tools to query and update pets, orders, and users in the Petstore demo API. All endpoints are available."
)

def make_api_request(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        if method.lower() == "get":
            response = requests.get(url, params=params, headers=headers)
        elif method.lower() == "post":
            response = requests.post(url, json=data, headers=headers)
        elif method.lower() == "put":
            response = requests.put(url, json=data, headers=headers)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers, params=params)
        else:
            return {"error": "Invalid HTTP method"}
        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

# def format_api_response(response):
#     if isinstance(response, dict) and "error" in response:
#         return f"Error: {response['error']}\n\nDetails: {response.get('details', 'No additional details')}"
#     return json.dumps(response, indent=2)

def get_openapi_spec():
    resp = requests.get(OPENAPI_URL)
    resp.raise_for_status()
    return resp.json()

def parse_parameters(parameters):
    """Convert OpenAPI parameters to Python function arguments."""
    args = []
    defaults = {}
    for param in parameters:
        name = param["name"]
        required = param.get("required", False)
        param_type = param.get("type", "str")
        if not required:
            defaults[name] = None
        args.append(name)
    return args, defaults

def build_func(endpoint, method, operation):
    """Dynamic tool function builder."""
    parameters = operation.get("parameters", [])
    args, defaults = parse_parameters(parameters)
    summary = operation.get("summary", f"{method.upper()} {endpoint}")

    def api_tool(**kwargs):
        # ... (your logic here)
        pass

    # Build correct signature
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
            tool_name = f"{method}_{endpoint.strip('/').replace('/', '_').replace('{','').replace('}','')}"
            mcp.tool(description=summary, name=tool_name)(func)

register_all_tools()

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run())
