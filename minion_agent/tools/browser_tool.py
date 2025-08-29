"""
Browser tool for Minion-Manus.

This module provides browser functionality that can be used with the Minion-Manus framework.
It is based on the browser_use_tool from OpenManus.
"""

import asyncio
import json
import multiprocessing
from typing import Any, Dict, List, Optional, Union
from queue import Empty
from multiprocessing import Process, Queue

from browser_use import Browser as BrowserUseBrowser
from browser_use.browser.context import BrowserContext
from browser_use.dom.service import DomService
from loguru import logger
from pydantic import BaseModel, Field

from smolagents import tool

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

class BrowserProcess:
    """Manages browser operations in a separate process."""
    def __init__(self):
        self.command_queue = Queue()
        self.result_queue = Queue()
        self.process = None
        self._start_process()

    def _start_process(self):
        """Start the browser process."""
        if self.process is None or not self.process.is_alive():
            self.process = Process(target=self._browser_worker, args=(self.command_queue, self.result_queue))
            self.process.start()

    def _browser_worker(self, cmd_queue: Queue, result_queue: Queue):
        """Worker function that runs in a separate process."""
        browser = None
        context = None
        
        try:
            # Initialize browser
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            browser = BrowserUseBrowser(headless=False)
            context = loop.run_until_complete(browser.new_context())
            
            while True:
                try:
                    cmd = cmd_queue.get(timeout=1)
                    if cmd is None:  # Shutdown signal
                        break
                        
                    action = cmd.get('action')
                    if action not in VALID_ACTIONS:
                        result_queue.put({
                            'success': False,
                            'message': f'Invalid action: {action}'
                        })
                        continue

                    # Handle the action
                    result = loop.run_until_complete(self._handle_action(context, cmd))
                    result_queue.put(result)
                    
                except Empty:
                    continue
                except Exception as e:
                    result_queue.put({
                        'success': False,
                        'message': f'Error: {str(e)}'
                    })
                    
        finally:
            if context:
                loop.run_until_complete(context.close())
            if browser:
                loop.run_until_complete(browser.close())
            loop.close()

    async def _handle_action(self, context: BrowserContext, cmd: Dict) -> Dict:
        """Handle a browser action."""
        action = cmd['action']
        try:
            if action == "navigate":
                page = await context.get_current_page()
                await page.goto(cmd['url'])
                return {'success': True, 'message': f"Navigated to {cmd['url']}"}
                
            elif action == "get_html":
                page = await context.get_current_page()
                html = await page.content()
                if len(html) > MAX_LENGTH:
                    html = html[:MAX_LENGTH] + "... (truncated)"
                return {'success': True, 'message': "HTML content retrieved", 'data': {'html': html}}

            elif action == "click":
                if cmd.get('index') is None:
                    return {'success': False, 'message': "Index is required for click action"}
                element = await context.get_dom_element_by_index(cmd['index'])
                if not element:
                    return {'success': False, 'message': f"Element with index {cmd['index']} not found"}
                await context._click_element_node(element)
                return {'success': True, 'message': f"Clicked element at index {cmd['index']}"}

            elif action == "input_text":
                if cmd.get('index') is None:
                    return {'success': False, 'message': "Index is required for input_text action"}
                if cmd.get('text') is None:
                    return {'success': False, 'message': "Text is required for input_text action"}
                element = await context.get_dom_element_by_index(cmd['index'])
                if not element:
                    return {'success': False, 'message': f"Element with index {cmd['index']} not found"}
                await context._input_text_element_node(element, cmd['text'])
                return {'success': True, 'message': f"Input text '{cmd['text']}' at index {cmd['index']}"}

            elif action == "screenshot":
                page = await context.get_current_page()
                screenshot = await page.screenshot()
                return {'success': True, 'message': "Screenshot captured", 'data': {"screenshot": screenshot}}

            elif action == "get_text":
                page = await context.get_current_page()
                text = await page.inner_text("body")
                if len(text) > MAX_LENGTH:
                    text = text[:MAX_LENGTH] + "... (truncated)"
                return {'success': True, 'message': "Text content retrieved", 'data': {"text": text}}

            elif action == "read_links":
                page = await context.get_current_page()
                elements = await page.query_selector_all("a")
                links = []
                for element in elements:
                    href = await element.get_attribute("href")
                    text = await element.inner_text()
                    if href:
                        links.append({"href": href, "text": text})
                return {'success': True, 'message': f"Found {len(links)} links", 'data': {"links": links}}

            elif action == "execute_js":
                if not cmd.get('script'):
                    return {'success': False, 'message': "Script is required for execute_js action"}
                page = await context.get_current_page()
                js_result = await page.evaluate(cmd['script'])
                return {'success': True, 'message': "JavaScript executed", 'data': {"result": str(js_result)}}

            elif action == "scroll":
                if cmd.get('scroll_amount') is None:
                    return {'success': False, 'message': "Scroll amount is required for scroll action"}
                page = await context.get_current_page()
                await page.evaluate(f"window.scrollBy(0, {cmd['scroll_amount']})")
                return {'success': True, 'message': f"Scrolled by {cmd['scroll_amount']} pixels"}

            elif action == "switch_tab":
                if cmd.get('tab_id') is None:
                    return {'success': False, 'message': "Tab ID is required for switch_tab action"}
                await context.switch_to_tab(cmd['tab_id'])
                return {'success': True, 'message': f"Switched to tab {cmd['tab_id']}"}

            elif action == "new_tab":
                if not cmd.get('url'):
                    return {'success': False, 'message': "URL is required for new_tab action"}
                await context.create_new_tab(cmd['url'])
                return {'success': True, 'message': f"Opened new tab with URL {cmd['url']}"}

            elif action == "close_tab":
                await context.close_current_tab()
                return {'success': True, 'message': "Closed current tab"}

            elif action == "refresh":
                page = await context.get_current_page()
                await page.reload()
                return {'success': True, 'message': "Page refreshed"}

            elif action == "get_current_state":
                state = await context.get_state()
                return {
                    'success': True,
                    'message': "Current browser state retrieved",
                    'data': {"url": state.url, "title": state.title}
                }
                
            return {'success': False, 'message': f'Action {action} not implemented'}
            
        except Exception as e:
            return {'success': False, 'message': f'Error executing {action}: {str(e)}'}

    def execute(self, **kwargs) -> Dict:
        """Execute a browser command."""
        self._start_process()  # Ensure process is running
        self.command_queue.put(kwargs)
        try:
            result = self.result_queue.get(timeout=30)  # 30 second timeout
            return result
        except Empty:
            return {'success': False, 'message': 'Operation timed out'}

    def cleanup(self):
        """Clean up resources."""
        if self.process and self.process.is_alive():
            self.command_queue.put(None)  # Send shutdown signal
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.terminate()
        self.process = None

# Global browser process instance
_browser_process = None

def get_browser_process():
    """Get or create the browser process."""
    global _browser_process
    if _browser_process is None:
        _browser_process = BrowserProcess()
    return _browser_process

#@tool
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
            - 'switch_tab': Switch to a specific tab
            - 'new_tab': Open a new tab
            - 'close_tab': Close the current tab
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
    browser_process = get_browser_process()
    result = browser_process.execute(
        action=action,
        url=url,
        index=index,
        text=text,
        script=script,
        scroll_amount=scroll_amount,
        tab_id=tab_id
    )
    return BrowserToolResult(**result).dict()

def cleanup():
    """Clean up browser resources."""
    global _browser_process
    if _browser_process:
        _browser_process.cleanup()
        _browser_process = None

async def get_current_state() -> Dict[str, Any]:
    """Get the current state of the browser.
    
    Returns:
        Dict containing the current URL and page title.
    """
    browser_process = get_browser_process()
    result = browser_process.execute(
        action="get_current_state"
    )
    return BrowserToolResult(**result).dict() 