#from tinyagent
"""
This module provides utility functions to run AppleScript and shell commands from Python.

Functions:
    run_applescript(script: str) -> str:
        Runs the given AppleScript using osascript and returns the result.

    run_applescript_capture(script: str) -> tuple[str, str]:
        Runs the given AppleScript using osascript, captures the output and error, and returns them.

    run_command(command) -> tuple[str, str]:
        Executes a shell command and returns the output and error.
"""
import subprocess
from typing import List


def run_applescript(script: str) -> str:
    """Runs the given AppleScript using osascript and returns the result.

    Args:
        script (str): The AppleScript code to execute.

    Returns:
        str: The standard output from the executed AppleScript.

    Raises:
        subprocess.CalledProcessError: If the AppleScript execution fails.
    """
    args = ["osascript", "-e", script]
    result = subprocess.check_output(args, universal_newlines=True)
    return result


def run_applescript_capture(script: str) -> List[str]:
    """Runs the given AppleScript using osascript, captures the output and error, and returns them.

    Args:
        script (str): The AppleScript code to execute.

    Returns:
        tuple[str, str]: A tuple containing the standard output and standard error.
    """
    args = ["osascript", "-e", script]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    stdout, stderr = result.stdout, result.stderr
    return [stdout, stderr]


def run_command(command: str) -> List[str]:
    """Executes a shell command and returns the output and error.

    Args:
        command (list or str): The shell command to execute. Can be a list of arguments
            or a string command.

    Returns:
        tuple[str, str]: A tuple containing the standard output and standard error.
    """
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    stdout, stderr = result.stdout, result.stderr
    return [stdout, stderr]
