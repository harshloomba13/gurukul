"""Tools for the coding agent."""

from .utils import create_sandbox
from .logger import logger

def execute_code(code: str, sbx=None):
    """
    Execute Python code in a sandboxed environment.
    
    Args:
        code: The Python code to execute
        sbx: Optional sandbox instance. If None, creates a new one.
    
    Returns:
        The result of code execution or error message
    """
    try:
        if sbx is None:
            sbx = create_sandbox()
        
        # Execute code in sandbox
        namespace = sbx.execute(code)
        
        # Try to get the result if there's a variable called 'result'
        if 'result' in namespace:
            return str(namespace['result'])
        
        return "Code executed successfully"
    except Exception as e:
        error_msg = f"Error executing code: {str(e)}"
        logger.error(error_msg)
        return error_msg

