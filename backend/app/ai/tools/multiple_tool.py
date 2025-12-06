from pydantic import BaseModel, Field

from .base import BaseTool


class MultipleSchema(BaseModel):
    a: int = Field(description="The first integer")
    b: int = Field(description="The second integer")


class MultipleTool(BaseTool):
    name = "multiple"
    description = "Useful function to multiply two numbers."
    input_schema = MultipleSchema

    def run(self, a: int, b: int) -> int:
        return a * b
