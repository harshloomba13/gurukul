"""Tool schemas for the coding agent."""

# OpenAI Responses API expects tools to include a top-level name and type.
# See https://platform.openai.com/docs/guides/function-calling for the shape.
execute_code_schema = {
    "name": "execute_code",
    "type": "function",
    "description": "Execute Python code in a sandboxed environment",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute",
            }
        },
        "required": ["code"],
    },
}

