"""Calculator tools for mathematical operations."""

import math

from pydantic import BaseModel, Field

from .base import BaseTool, ToolOutput


# Input Schemas
class AddSchema(BaseModel):
    """Schema for adding two numbers."""

    a: float = Field(description="First number to add")
    b: float = Field(description="Second number to add")


class MultiplySchema(BaseModel):
    """Schema for multiplying two numbers."""

    a: float = Field(description="First number to multiply")
    b: float = Field(description="Second number to multiply")


class PowerSchema(BaseModel):
    """Schema for raising a number to a power."""

    base: float = Field(description="Base number")
    exponent: float = Field(description="Exponent to raise the base to")


class FactorialSchema(BaseModel):
    """Schema for calculating factorial."""

    n: int = Field(description="Non-negative integer to calculate factorial for")


# Tools
class AddTool(BaseTool):
    """Tool for adding two numbers together."""

    name = "add"
    description = "Add two numbers together and return the sum"
    input_schema = AddSchema

    async def arun(self, a: float, b: float) -> ToolOutput:
        try:
            result = a + b
            return ToolOutput(type="json", value=result)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))


class MultiplyTool(BaseTool):
    """Tool for multiplying two numbers."""

    name = "multiply"
    description = "Multiply two numbers together and return the product"
    input_schema = MultiplySchema

    async def arun(self, a: float, b: float) -> str:
        try:
            result = a * b
            return ToolOutput(type="json", value=result)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))


class PowerTool(BaseTool):
    """Tool for raising a number to a power."""

    name = "power"
    description = "Raise a base number to an exponent and return the result"
    input_schema = PowerSchema

    async def arun(self, base: float, exponent: float) -> str:
        try:
            result = base**exponent
            return ToolOutput(type="json", value=result)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))


class FactorialTool(BaseTool):
    """Tool for calculating factorial of a non-negative integer."""

    name = "factorial"
    description = "Calculate the factorial of a non-negative integer"
    input_schema = FactorialSchema

    async def arun(self, n: int) -> str:
        try:
            if n < 0:
                return ToolOutput(
                    type="error-text",
                    value="Factorial is not defined for negative numbers",
                )
            result = math.factorial(n)
            return ToolOutput(type="json", value=result)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))
