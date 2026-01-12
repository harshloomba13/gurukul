"""Utility functions for the coding agent."""

class Sandbox:
    """A simple sandbox for code execution."""
    def __init__(self):
        self.namespace = {}
    
    def execute(self, code: str):
        """Execute code in the sandbox namespace."""
        exec(code, self.namespace)
        return self.namespace

def create_sandbox():
    """Create a new sandbox instance."""
    return Sandbox()

