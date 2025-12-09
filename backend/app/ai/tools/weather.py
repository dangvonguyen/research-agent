import random

from pydantic import BaseModel, Field

from .base import BaseTool, ToolOutput


# Input Schemas
class CurrentWeatherSchema(BaseModel):
    """Schema for getting current weather."""

    location: str = Field(description="City name or location to get weather for")


class ForecastSchema(BaseModel):
    """Schema for getting weather forecast."""

    location: str = Field(description="City name or location to get forecast for")
    days: int = Field(
        default=7, description="Number of days to forecast (1-7)", ge=1, le=7
    )


class CompareWeatherSchema(BaseModel):
    """Schema for comparing weather between locations."""

    location1: str = Field(description="First city/location")
    location2: str = Field(description="Second city/location")


# Tools
class CurrentWeatherTool(BaseTool):
    """Tool for getting current weather for a location (mock data)."""

    name = "get_current_weather"
    description = (
        "Get current weather conditions for a specified location. "
        "Returns temperature, conditions, humidity, and wind speed."
    )
    input_schema = CurrentWeatherSchema

    async def arun(self, location: str) -> ToolOutput:
        try:
            # Mock weather data for POC
            conditions_options = [
                "sunny",
                "partly cloudy",
                "cloudy",
                "rainy",
                "stormy",
            ]
            mock_weather = {
                "location": location,
                "temperature": random.randint(45, 85),
                "temperature_unit": "F",
                "conditions": random.choice(conditions_options),
                "humidity": random.randint(30, 90),
                "wind_speed": random.randint(0, 20),
                "wind_unit": "mph",
            }
            return ToolOutput(type="json", value=mock_weather)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))


class ForecastTool(BaseTool):
    """Tool for getting weather forecast (mock data)."""

    name = "get_forecast"
    description = (
        "Get weather forecast for a location for the next 1-7 days. "
        "Returns daily forecasts with high/low temperatures and conditions."
    )
    input_schema = ForecastSchema

    async def arun(self, location: str, days: int = 7) -> ToolOutput:
        try:
            if days < 1 or days > 7:
                return ToolOutput(
                    type="error-text", value="Days must be between 1 and 7"
                )

            conditions_options = [
                "sunny",
                "partly cloudy",
                "cloudy",
                "rainy",
                "stormy",
            ]

            # Generate mock forecast
            forecast_days = []
            for i in range(days):
                forecast_days.append(
                    {
                        "day": i + 1,
                        "high": random.randint(55, 85),
                        "low": random.randint(35, 65),
                        "conditions": random.choice(conditions_options),
                        "precipitation_chance": random.randint(0, 100),
                    }
                )

            mock_forecast = {
                "location": location,
                "days": days,
                "forecast": forecast_days,
                "temperature_unit": "F",
            }
            return ToolOutput(type="json", value=mock_forecast)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))


class CompareWeatherTool(BaseTool):
    """Tool for comparing weather between two locations (mock data)."""

    name = "compare_weather"
    description = (
        "Compare current weather conditions between two locations. "
        "Returns side-by-side comparison of temperature, conditions, etc."
    )
    input_schema = CompareWeatherSchema

    async def arun(self, location1: str, location2: str) -> str:
        try:
            conditions_options = [
                "sunny",
                "partly cloudy",
                "cloudy",
                "rainy",
                "stormy",
            ]

            # Generate mock weather for both locations
            location1_weather = {
                "location": location1,
                "temperature": random.randint(45, 85),
                "conditions": random.choice(conditions_options),
                "humidity": random.randint(30, 90),
            }

            location2_weather = {
                "location": location2,
                "temperature": random.randint(45, 85),
                "conditions": random.choice(conditions_options),
                "humidity": random.randint(30, 90),
            }

            # Calculate differences
            temp_diff = abs(
                location1_weather["temperature"] - location2_weather["temperature"]
            )
            warmer_location = (
                location1
                if location1_weather["temperature"] > location2_weather["temperature"]
                else location2
            )

            comparison = {
                "location1": location1_weather,
                "location2": location2_weather,
                "temperature_difference": temp_diff,
                "temperature_unit": "F",
                "warmer_location": warmer_location,
            }
            return ToolOutput(type="json", value=comparison)
        except Exception as e:
            return ToolOutput(type="error-text", value=str(e))
