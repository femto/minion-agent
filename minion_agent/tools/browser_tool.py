"""
Browser tool for Minion-Manus.

This module provides browser functionality that can be used with the Minion-Manus framework.
Updated for browser-use 0.8.0 API.
"""

import asyncio
from typing import Any, Dict, Optional

from browser_use import Browser as BrowserUseBrowser
from loguru import logger
from pydantic import BaseModel

MAX_LENGTH = 128_000

# Valid browser actions
VALID_ACTIONS = {
    "navigate", "click", "input_text", "screenshot", "get_html",
    "get_text", "read_links", "execute_js", "scroll", "switch_tab",
    "new_tab", "close_tab", "refresh"
}

class BrowserToolResult(BaseModel):
    """Result of a browser tool execution."""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None

# Global browser instance
_browser = None

async def get_browser():
    """Get or create the browser instance."""
    global _browser
    if _browser is None:
        _browser = BrowserUseBrowser(headless=False)
        await _browser.start()
    return _browser

async def _handle_action(browser: BrowserUseBrowser, cmd: Dict) -> Dict:
    """Handle a browser action."""
    action = cmd['action']
    try:
        if action == "navigate":
            page = await browser.get_current_page()
            await page.goto(cmd['url'])
            return {'success': True, 'message': f"Navigated to {cmd['url']}"}
            
        elif action == "get_html":
            page = await browser.get_current_page()
            html = await page.evaluate("document.documentElement.outerHTML")
            if len(html) > MAX_LENGTH:
                html = html[:MAX_LENGTH] + "... (truncated)"
            return {'success': True, 'message': "HTML content retrieved", 'data': {'html': html}}

        elif action == "click":
            if cmd.get('index') is None:
                return {'success': False, 'message': "Index is required for click action"}
            element = await browser.get_dom_element_by_index(cmd['index'])
            if not element:
                return {'success': False, 'message': f"Element with index {cmd['index']} not found"}
            
            # Get the actual element to click
            page = await browser.get_current_page()
            cdp_element = page.get_element(element.backend_node_id)
            await cdp_element.click()
            return {'success': True, 'message': f"Clicked element at index {cmd['index']}"}

        elif action == "input_text":
            if cmd.get('index') is None:
                return {'success': False, 'message': "Index is required for input_text action"}
            if cmd.get('text') is None:
                return {'success': False, 'message': "Text is required for input_text action"}
            element = await browser.get_dom_element_by_index(cmd['index'])
            if not element:
                return {'success': False, 'message': f"Element with index {cmd['index']} not found"}
            
            # Get the actual element to fill
            page = await browser.get_current_page()
            cdp_element = page.get_element(element.backend_node_id)
            await cdp_element.fill(cmd['text'])
            return {'success': True, 'message': f"Input text '{cmd['text']}' at index {cmd['index']}"}

        elif action == "screenshot":
            page = await browser.get_current_page()
            screenshot = await page.screenshot()
            return {'success': True, 'message': "Screenshot captured", 'data': {"screenshot": screenshot}}

        elif action == "get_text":
            page = await browser.get_current_page()
            text = await page.evaluate("document.body.innerText")
            if len(text) > MAX_LENGTH:
                text = text[:MAX_LENGTH] + "... (truncated)"
            return {'success': True, 'message': "Text content retrieved", 'data': {"text": text}}

        elif action == "read_links":
            page = await browser.get_current_page()
            elements = await page.get_elements_by_css_selector("a")
            links = []
            for element in elements:
                href = await element.get_attribute("href")
                # Get text content using JavaScript
                text = await page.evaluate(f"""
                    (() => {{
                        const links = document.querySelectorAll('a[href="{href}"]');
                        return links.length > 0 ? links[0].innerText : '';
                    }})()
                """)
                if href:
                    links.append({"href": href, "text": text})
            return {'success': True, 'message': f"Found {len(links)} links", 'data': {"links": links}}

        elif action == "execute_js":
            if not cmd.get('script'):
                return {'success': False, 'message': "Script is required for execute_js action"}
            page = await browser.get_current_page()
            js_result = await page.evaluate(cmd['script'])
            return {'success': True, 'message': "JavaScript executed", 'data': {"result": str(js_result)}}

        elif action == "scroll":
            if cmd.get('scroll_amount') is None:
                return {'success': False, 'message': "Scroll amount is required for scroll action"}
            page = await browser.get_current_page()
            await page.evaluate(f"window.scrollBy(0, {cmd['scroll_amount']})")
            return {'success': True, 'message': f"Scrolled by {cmd['scroll_amount']} pixels"}

        elif action == "new_tab":
            if not cmd.get('url'):
                return {'success': False, 'message': "URL is required for new_tab action"}
            page = await browser.new_page()
            await page.goto(cmd['url'])
            return {'success': True, 'message': f"Opened new tab with URL {cmd['url']}"}

        elif action == "refresh":
            page = await browser.get_current_page()
            await page.reload()
            return {'success': True, 'message': "Page refreshed"}

        elif action == "get_current_state":
            page = await browser.get_current_page()
            url = await page.get_url()
            title = await page.get_title()
            return {
                'success': True,
                'message': "Current browser state retrieved",
                'data': {"url": url, "title": title}
            }
            
        return {'success': False, 'message': f'Action {action} not implemented'}
        
    except Exception as e:
        return {'success': False, 'message': f'Error executing {action}: {str(e)}'}

def browser(
    action: str,
    url: Optional[str] = None,
    index: Optional[int] = None,
    text: Optional[str] = None,
    script: Optional[str] = None,
    scroll_amount: Optional[int] = None,
    tab_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute browser actions to interact with web pages.

    This function provides various browser operations including navigation, element interaction,
    content extraction, and tab management.

    Args:
        action: The browser action to perform. Must be one of:
            - 'navigate': Go to a specific URL
            - 'click': Click an element by index
            - 'input_text': Input text into an element
            - 'screenshot': Capture a screenshot
            - 'get_html': Get page HTML content
            - 'get_text': Get text content of the page
            - 'read_links': Get all links on the page
            - 'execute_js': Execute JavaScript code
            - 'scroll': Scroll the page
            - 'new_tab': Open a new tab
            - 'refresh': Refresh the current page
        url: URL for navigation actions
        index: Element index for click/input actions
        text: Text for input actions
        script: JavaScript code to execute
        scroll_amount: Amount to scroll in pixels
        tab_id: Tab ID for tab management actions

    Returns:
        Dict containing:
            - success: Whether the action was successful
            - message: Description of what happened
            - data: Optional data returned by the action
    """
    if action not in VALID_ACTIONS:
        return BrowserToolResult(
            success=False, 
            message=f'Invalid action: {action}'
        ).dict()
    
    try:
        # Run the async action in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_action():
            browser_instance = await get_browser()
            return await _handle_action(browser_instance, {
                'action': action,
                'url': url,
                'index': index,
                'text': text,
                'script': script,
                'scroll_amount': scroll_amount,
                'tab_id': tab_id
            })
        
        result = loop.run_until_complete(run_action())
        return BrowserToolResult(**result).dict()
        
    except Exception as e:
        return BrowserToolResult(
            success=False,
            message=f'Error: {str(e)}'
        ).dict()

async def cleanup():
    """Clean up browser resources."""
    global _browser
    if _browser:
        await _browser.stop()
        _browser = None

async def get_current_state() -> Dict[str, Any]:
    """Get the current state of the browser.
    
    Returns:
        Dict containing the current URL and page title.
    """
    try:
        browser_instance = await get_browser()
        result = await _handle_action(browser_instance, {'action': 'get_current_state'})
        return BrowserToolResult(**result).dict()
    except Exception as e:
        return BrowserToolResult(
            success=False,
            message=f'Error: {str(e)}'
        ).dict() 