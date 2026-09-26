import os
import re

import requests
from requests.exceptions import RequestException


def _truncate_content(content: str, max_length: int) -> str:
    if len(content) <= max_length:
        return content
    return (
        content[: max_length // 2]
        + f"\n..._This content has been truncated to stay below {max_length} characters_...\n"
        + content[-max_length // 2 :]
    )


def search_web(query: str) -> str:
    """Perform a duckduckgo web search based on your query (think a Google search) then returns the top search results.

    Args:
        query (str): The search query to perform.

    Returns:
        The top search results.

    """
    try:
        from duckduckgo_search import DDGS  # type: ignore[import-not-found]
    except ImportError as e:
        msg = "You need to `pip install 'duckduckgo_search'` to use this tool"
        raise ImportError(msg) from e

    ddgs = DDGS()
    results = ddgs.text(query, max_results=10)
    return "\n".join(
        f"[{result['title']}]({result['href']})\n{result['body']}" for result in results
    )


def visit_webpage(url: str, timeout: int = 30, max_length: int = 10000) -> str:
    """Visits a webpage at the given url and reads its content as a markdown string. Use this to browse webpages.

    Args:
        url: The url of the webpage to visit.
        timeout: The timeout in seconds for the request.
        max_length: The maximum number of characters of text that can be returned (default=10000).
                    If max_length==-1, text is not truncated and the full webpage is returned.

    """
    try:
        from markdownify import markdownify  # type: ignore[import-not-found]
    except ImportError as e:
        msg = "You need to `pip install 'markdownify'` to use this tool"
        raise ImportError(msg) from e

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        markdown_content = markdownify(response.text).strip()

        markdown_content = re.sub(r"\n{2,}", "\n", markdown_content)

        if max_length == -1:
            return str(markdown_content)
        return _truncate_content(markdown_content, max_length)
    except RequestException as e:
        return f"Error fetching the webpage: {e!s}"
    except Exception as e:
        return f"An unexpected error occurred: {e!s}"


def search_tavily(query: str, include_images: bool = False) -> str:
    """Perform a Tavily web search based on your query and return the top search results.

    See https://blog.tavily.com/getting-started-with-the-tavily-search-api for more information.

    Args:
        query (str): The search query to perform.
        include_images (bool): Whether to include images in the results.

    Returns:
        The top search results as a formatted string.

    """
    try:
        from tavily.tavily import TavilyClient
    except ImportError as e:
        msg = "You need to `pip install 'tavily-python'` to use this tool"
        raise ImportError(msg) from e

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY environment variable not set."
    try:
        client = TavilyClient(api_key)
        response = client.search(query, include_images=include_images)
        results = response.get("results", [])
        output = []
        for result in results:
            output.append(
                f"[{result.get('title', 'No Title')}]({result.get('url', '#')})\n{result.get('content', '')}"
            )
        if include_images and "images" in response:
            output.append("\nImages:")
            for image in response["images"]:
                output.append(image)
        return "\n\n".join(output) if output else "No results found."
    except Exception as e:
        return f"Error performing Tavily search: {e!s}"


def search_youcom(query: str, max_results: int = 5) -> str:
    """Perform a You.com web search based on your query and return the top search results.

    Uses the You.com Search API (https://you.com/docs/api-reference/search).
    Requires the YDC_API_KEY environment variable (get a key at
    https://you.com/platform/api-keys).

    Args:
        query (str): The search query to perform.
        max_results (int): The maximum number of results to return (default=5).

    Returns:
        The top search results as a formatted string.

    """
    api_key = os.getenv("YDC_API_KEY")
    if not api_key:
        return "YDC_API_KEY environment variable not set."

    try:
        # You.com Search API accepts `count` in the 1-100 range; clamp so
        # out-of-range values don't trigger an HTTP 400. The conversion sits
        # inside the try so a non-numeric max_results degrades to a returned
        # error message instead of an unhandled exception.
        count = max(1, min(int(max_results), 100))
        response = requests.post(
            "https://ydc-index.io/v1/search",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"query": query, "count": count},
            timeout=30,
        )
        response.raise_for_status()
        web_results = response.json().get("results", {}).get("web", [])
        output = []
        for result in web_results:
            description = result.get("description", "")
            snippets = result.get("snippets") or []
            snippet = snippets[0] if snippets else description
            output.append(
                f"[{result.get('title', 'No Title')}]({result.get('url', '#')})\n{snippet}"
            )
        return "\n\n".join(output) if output else "No results found."
    except RequestException as e:
        return f"Error fetching You.com search: {e!s}"
    except Exception as e:
        return f"An unexpected error occurred: {e!s}"


def search_serply(query: str, max_results: int = 5) -> str:
    """Perform a Serply web search (Google results) based on your query and return the top search results.

    Uses the Serply Search API (https://serply.io/docs).
    Requires the SERPLY_API_KEY environment variable (get a key at
    https://serply.io, the free tier includes 2,500 credits).

    Args:
        query (str): The search query to perform.
        max_results (int): The maximum number of results to return (default=5).

    Returns:
        The top search results as a formatted string.

    """
    api_key = os.getenv("SERPLY_API_KEY")
    if not api_key:
        return "SERPLY_API_KEY environment variable not set."

    try:
        # Serply returns at most 10 results per request; clamp to 1-10. The
        # conversion sits inside the try so a non-numeric max_results degrades
        # to a returned error message instead of an unhandled exception.
        num = max(1, min(int(max_results), 10))
        response = requests.get(
            "https://api.serply.io/v1/search",
            params={"q": query, "num": num},
            headers={"X-Api-Key": api_key, "User-Agent": "minion-agent"},
            timeout=30,
        )
        response.raise_for_status()
        results = response.json().get("results", [])[:num]
        output = [
            f"[{result.get('title', 'No Title')}]({result.get('link', '#')})\n{result.get('description', '')}"
            for result in results
        ]
        return "\n\n".join(output) if output else "No results found."
    except RequestException as e:
        return f"Error fetching Serply search: {e!s}"
    except Exception as e:
        return f"An unexpected error occurred: {e!s}"
