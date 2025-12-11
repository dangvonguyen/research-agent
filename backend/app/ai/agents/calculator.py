from llama_index.core.tools import BaseTool as LlamaBaseTool

from app.ai.prompts import CALCULATOR_AGENT_PROMPT
from app.ai.tools.calculator import (
    AddTool,
    FactorialTool,
    MultiplyTool,
    PowerTool,
)

from .base import BaseAgent


class CalculatorAgent(BaseAgent):
    """Agent specialized in mathematical calculations.

    Provides capabilities for:
    - Addition
    - Multiplication
    - Exponentiation
    - Factorial calculation
    """

    @property
    def name(self) -> str:
        return "calculator_agent"

    @property
    def description(self) -> str:
        return (
            "Delegate to Calculator Agent for mathematical calculations. "
            "Use for: addition, multiplication, exponentiation, factorial, "
            "and any multi-step mathematical problems."
        )

    @property
    def capabilities(self) -> list[str]:
        return ["addition", "multiplication", "exponentiation", "factorial", "math"]

    def get_tools(self) -> list[LlamaBaseTool]:
        return [
            AddTool.as_tool(),
            MultiplyTool.as_tool(),
            PowerTool.as_tool(),
            FactorialTool.as_tool(),
        ]

    def get_system_prompt(self) -> str:
        return CALCULATOR_AGENT_PROMPT
