from mcp.server.fastmcp import FastMCP, Context
import requests
import json

# Create an MCP server
mcp = FastMCP(
    name="PetstoreAPI",
    description="Interact with the Petstore Swagger API",
    instructions="Use these tools to query and update pets, orders, and users in the Petstore demo API."
)

# Base URL for the Petstore API
BASE_URL = "https://petstore.swagger.io/v2"

# Helper function to make API requests
def make_api_request(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    try:
        if method.lower() == "get":
            response = requests.get(url, params=params, headers=headers)
        elif method.lower() == "post":
            response = requests.post(url, json=data, headers=headers)
        elif method.lower() == "put":
            response = requests.put(url, json=data, headers=headers)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers)
        else:
            return {"error": "Invalid HTTP method"}
        
        # Handle HTTP errors
        if response.status_code >= 400:
            return {
                "error": f"API returned status code {response.status_code}",
                "details": response.text
            }
            
        # Handle JSON parsing errors
        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def format_api_response(response, query_context=""):
    """Format API responses for better readability"""
    if isinstance(response, dict) and "error" in response:
        return f"Error: {response['error']}\n\nDetails: {response.get('details', 'No additional details')}"
    
    # If it's a list of items, summarize the count
    if isinstance(response, list):
        count = len(response)
        if count == 0:
            return "No items found."
        
        if query_context.lower().startswith("find pet"):
            summary = f"Found {count} pet{'s' if count > 1 else ''}:\n\n"
            for pet in response[:5]:  # Limit to first 5 for readability
                summary += f"- {pet.get('name', 'Unnamed')} (ID: {pet.get('id', 'Unknown')}): {pet.get('status', 'Unknown status')}\n"
            
            if count > 5:
                summary += f"\n... and {count - 5} more pets"
            
            return summary
            
    # Default to pretty JSON
    return json.dumps(response, indent=2)

# Pet-related tools
@mcp.tool(description="Find pets by status (available, pending, sold)")
def find_pets_by_status(status: str = "available") -> str:
    """
    Find pets by their status.
    
    Args:
        status: Status values to filter by (available, pending, sold)
    
    Returns:
        List of pets with the specified status
    """
    result = make_api_request("get", "pet/findByStatus", params={"status": status})
    return format_api_response(result, query_context="Find pets by their status")

@mcp.tool(description="Get pet details by ID")
def get_pet_by_id(pet_id: int) -> str:
    """
    Find a pet by its ID.
    
    Args:
        pet_id: The ID of the pet to retrieve
    
    Returns:
        Pet details
    """
    result = make_api_request("get", f"pet/{pet_id}")
    return format_api_response(result, query_context="Find a pet by its ID")

@mcp.tool(description="Find pets by tags")
def find_pets_by_tags(tags: str) -> str:
    """
    Find pets by tags (comma-separated).
    
    Args:
        tags: Tags to filter by (comma-separated)
    
    Returns:
        List of pets with the specified tags
    """
    tag_list = [tag.strip() for tag in tags.split(",")]
    result = make_api_request("get", "pet/findByTags", params={"tags": tag_list})
    return format_api_response(result, query_context="Find pets by tags")


# Store-related tools
@mcp.tool(description="Get inventory status by status")
def get_inventory() -> str:
    """
    Returns pet inventory by status.
    
    Returns:
        Map of status to quantity
    """
    result = make_api_request("get", "store/inventory")
    return format_api_response(result, query_context="Returns pet inventory by status")

@mcp.tool(description="Place an order for a pet")
def place_order(
    pet_id: int,
    quantity: int = 1,
    status: str = "placed",
    complete: bool = False
) -> str:
    """
    Place a new order in the store.
    
    Args:
        pet_id: ID of pet to order
        quantity: Quantity to order
        status: Order status
        complete: Whether the order is complete
    
    Returns:
        Order details
    """
    order_data = {
        "petId": pet_id,
        "quantity": quantity,
        "status": status,
        "complete": complete
    }
    result = make_api_request("post", "store/order", data=order_data)
    return format_api_response(result, query_context="Place a new order in the store")

@mcp.tool(description="Get order by ID")
def get_order_by_id(order_id: int) -> str:
    """
    Find purchase order by ID.
    
    Args:
        order_id: ID of the order to fetch
    
    Returns:
        Order details
    """
    result = make_api_request("get", f"store/order/{order_id}")
    return format_api_response(result, query_context="Find purchase order by ID")


# User-related tools
@mcp.tool(description="Create a new user")
def create_user(
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    phone: str = "",
    user_status: int = 0
) -> str:
    """
    Create a new user.
    
    Args:
        username: Username
        first_name: First name
        last_name: Last name
        email: Email address
        password: Password
        phone: Phone number
        user_status: User status
    
    Returns:
        Result of creating the user
    """
    user_data = {
        "username": username,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "password": password,
        "phone": phone,
        "userStatus": user_status
    }
    result = make_api_request("post", "user", data=user_data)
    return format_api_response(result, query_context="Create a new user")

@mcp.tool(description="Get user by username")
def get_user_by_username(username: str) -> str:
    """
    Get user by username.
    
    Args:
        username: The username to look up
    
    Returns:
        User details
    """
    result = make_api_request("get", f"user/{username}")
    return format_api_response(result, query_context="Get user by username")

@mcp.tool(description="Login with user credentials")
def login_user(username: str, password: str) -> str:
    """
    Login a user.
    
    Args:
        username: Username
        password: Password
    
    Returns:
        Login status and session token
    """
    result = make_api_request("get", "user/login", params={"username": username, "password": password})
    return format_api_response(result, query_context="Login a user")


@mcp.tool(description="Query the Petstore API with natural language")
def query_petstore(query: str) -> str:
    """
    Free-form query tool for the Petstore API. You can describe what information 
    you want, and the agent will try to return the appropriate data.
    
    Examples:
    - "Find available pets"
    - "Get details for pet with ID 10"
    - "Check store inventory"
    - "Look up order #1"
    
    Args:
        query: Natural language query about pets, store, or users
        
    Returns:
        Relevant API response based on the query
    """
    # This is a meta-tool that should guide the model to use the other specific tools
    # The agent should analyze the query and decide which specific tool to use
    return """
    I understand you want information from the Petstore API. 
    To best help you, I'll need to call one of the specific API tools.
    
    Please let me analyze your query and call the appropriate tool.
    """

if __name__ == "__main__":
    # Run the server
    import asyncio
    asyncio.run(mcp.run())

