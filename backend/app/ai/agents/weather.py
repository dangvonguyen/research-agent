from llama_index.core.tools import BaseTool as LlamaBaseTool

from app.ai.prompts import WEATHER_AGENT_PROMPT
from app.ai.tools.weather import (
    CompareWeatherTool,
    CurrentWeatherTool,
    ForecastTool,
)

from .base import BaseAgent


class WeatherAgent(BaseAgent):
    """Agent specialized in weather information retrieval.

    Provides capabilities for:
    - Current weather conditions
    - Weather forecasts
    - Location weather comparison
    """

    @property
    def name(self) -> str:
        return "weather_agent"

    @property
    def description(self) -> str:
        return (
            "Delegate to Weather Agent for weather information. "
            "Use for: current weather, forecasts, location comparisons, "
            "and any weather-related queries."
        )

    @property
    def capabilities(self) -> list[str]:
        return [
            "current_weather",
            "weather_forecast",
            "weather_comparison",
            "weather",
        ]

    def get_tools(self) -> list[LlamaBaseTool]:
        return [
            CurrentWeatherTool.as_tool(),
            ForecastTool.as_tool(),
            CompareWeatherTool.as_tool(),
        ]

    def get_system_prompt(self) -> str:
        return WEATHER_AGENT_PROMPT
