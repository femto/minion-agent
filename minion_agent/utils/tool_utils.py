"""Utility functions for tool processing."""


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool name to be a valid Python identifier.
    
    Converts hyphens to underscores and ensures the name is a valid Python identifier.
    This is particularly useful for MCP tools that may have names with hyphens.
    
    Args:
        name: The original tool name (e.g., "search-web", "file-read")
        
    Returns:
        A sanitized name that's a valid Python identifier (e.g., "search_web", "file_read")
    """
    # Replace hyphens with underscores
    sanitized = name.replace("-", "_")
    
    # Ensure it starts with a letter or underscore
    if sanitized and not (sanitized[0].isalpha() or sanitized[0] == "_"):
        sanitized = f"tool_{sanitized}"
    
    # Replace any other invalid characters with underscores
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized)
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_tool"
        
    return sanitized