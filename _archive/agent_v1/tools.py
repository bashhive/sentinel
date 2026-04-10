"""
Tools/Functions that Aspasia can use
"""

import json
from typing import Any, Callable, Dict, List


class ToolRegistry:
    """Registry for tools that the agent can use"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register built-in tools"""
        self.register("get_time", self._get_time)
        self.register("calculate", self._calculate)
        self.register("store_memory", self._store_memory)
    
    def register(self, name: str, func: Callable) -> None:
        """Register a new tool"""
        self.tools[name] = func
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools in Claude format"""
        return [
            {
                "name": "get_time",
                "description": "Get current date and time",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "calculate",
                "description": "Perform mathematical calculations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression (e.g., '2 + 2 * 3')"
                        }
                    },
                    "required": ["expression"]
                }
            },
            {
                "name": "store_memory",
                "description": "Store important information for future reference",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Memory key"},
                        "value": {"type": "string", "description": "Memory value"}
                    },
                    "required": ["key", "value"]
                }
            }
        ]
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool"""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            return self.tools[tool_name](**kwargs)
        except Exception as e:
            return {"error": str(e)}
    
    # Built-in tools
    @staticmethod
    def _get_time() -> Dict[str, str]:
        """Get current time"""
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "message": f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    
    @staticmethod
    def _calculate(expression: str) -> Dict[str, Any]:
        """Evaluate mathematical expression safely"""
        try:
            # Simple safe evaluation (no eval())
            result = eval(expression, {"__builtins__": {}}, {})
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}
    
    @staticmethod
    def _store_memory(key: str, value: str) -> Dict[str, str]:
        """Store memory (placeholder - integrate with database)"""
        return {
            "status": "stored",
            "key": key,
            "message": f"Memory '{key}' stored successfully"
        }


# Global tool registry
tool_registry = ToolRegistry()
