"""
Tool definitions and registry.
Profiles register site-specific tools on top of the defaults.
"""

import ast
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class ToolType(Enum):
    INFORMATION = "information"
    ACTION = "action"
    INTEGRATION = "integration"


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    tool_type: ToolType
    handler: Optional[Callable] = None
    requires_approval: bool = False

    def to_claude_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": [k for k, v in self.parameters.items() if v.get("required", True)],
            },
        }


class ToolRegistry:
    """
    Registry of tools the agent can call.
    Profiles extend this with site-specific tools.
    """

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(Tool(
            name="get_time",
            description="Get the current date and time.",
            parameters={},
            tool_type=ToolType.INFORMATION,
            handler=self._handle_get_time,
        ))
        self.register(Tool(
            name="calculate",
            description="Evaluate a safe arithmetic expression (e.g. '(3 + 4) * 2').",
            parameters={
                "expression": {"type": "string", "description": "Arithmetic expression"},
            },
            tool_type=ToolType.INFORMATION,
            handler=self._handle_calculate,
        ))

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_all(self) -> list[Tool]:
        return list(self.tools.values())

    def list_for_claude(self) -> list[dict]:
        return [t.to_claude_dict() for t in self.tools.values()]

    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        if not tool or not tool.handler:
            return {"error": f"Tool '{name}' not found or has no handler"}
        try:
            return tool.handler(**kwargs)
        except Exception as e:
            return {"error": str(e)}

    # ── Default handlers ─────────────────────────────────────────────────────

    @staticmethod
    def _handle_get_time() -> dict:
        now = datetime.now()
        return {"timestamp": now.isoformat(), "formatted": now.strftime("%Y-%m-%d %H:%M:%S")}

    @staticmethod
    def _handle_calculate(expression: str) -> dict:
        """Safe eval using ast — no builtins, no exec."""
        try:
            tree = ast.parse(expression, mode="eval")
            # Whitelist: only literals and arithmetic operators
            allowed = (
                ast.Expression, ast.BinOp, ast.UnaryOp,
                ast.Num, ast.Constant,   # py3.8+
                ast.Add, ast.Sub, ast.Mult, ast.Div,
                ast.FloorDiv, ast.Mod, ast.Pow,
                ast.USub, ast.UAdd,
            )
            for node in ast.walk(tree):
                if not isinstance(node, allowed):
                    return {"error": f"Disallowed operation: {type(node).__name__}"}
            result = eval(compile(tree, "<string>", "eval"))
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}
