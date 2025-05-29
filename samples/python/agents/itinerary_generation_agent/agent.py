"""Crew AI based sample for A2A protocol.

Handles the agents and also presents the tools required.
"""

import base64
from io import BytesIO
import os
import re
import logging
from typing import Any, AsyncIterable, Dict
from uuid import uuid4

from PIL import Image
from crewai import LLM, Agent, Crew, Task
from crewai.process import Process
from crewai.tools import tool
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel


load_dotenv()

logger = logging.getLogger(__name__)


class Imagedata(BaseModel):
    """Represents image data.

    Attributes:
      id: Unique identifier for the image.
      name: Name of the image.
      mime_type: MIME type of the image.
      bytes: Base64 encoded image data.
      error: Error message if there was an issue with the image.
    """

    id: str | None = None
    name: str | None = None
    mime_type: str | None = None
    bytes: str | None = None
    error: str | None = None

class ItineraryGenerationAgent:
    """Agent that generates itineraries based on user prompts."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        if os.getenv('GOOGLE_API_KEY'):
            self.model = LLM(
                model='gemini/gemini-2.0-flash',
                api_key=os.getenv('GOOGLE_API_KEY'),
            )

        self.itinerary_creator_agent = Agent(
            role='Itinerary Creation Expert',
            goal="Generate an itinerary based on the user's text prompt",
            backstory=(
            "You are a seasoned travel consultant with over 15 years of experience "
            "in crafting personalized itineraries for travelers worldwide. You have "
            "extensive knowledge of destinations, cultural insights, optimal travel "
            "routes, seasonal considerations, and budget management. You excel at "
            "understanding traveler preferences, time constraints, and creating "
            "realistic, enjoyable experiences that balance must-see attractions "
            "with local hidden gems. Your itineraries always consider practical "
            "factors like transportation, accommodation proximity, meal timing, "
            "and rest periods to ensure a smooth and memorable journey."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.model,
        )

        self.itinerary_creation_task = Task(
            description=(
            "Analyze the user's travel request: '{user_prompt}' and create a detailed, "
            "personalized itinerary. Consider the destination, duration, budget, travel "
            "preferences, and any specific requirements mentioned. Structure the itinerary "
            "with daily activities, recommended timings, transportation options, dining "
            "suggestions, and practical tips. Ensure the itinerary is realistic, well-paced, "
            "and includes both popular attractions and local experiences."
            ),
            expected_output='The itinerary details in markdown format.',
            agent=self.itinerary_creator_agent,
        )

        self.itinerary_crew = Crew(
            agents=[self.itinerary_creator_agent],
            tasks=[self.itinerary_creation_task],
            process=Process.sequential,
            verbose=False,
        )

    def invoke(self, query, session_id) -> str:
        """Kickoff CrewAI and return the response."""
        inputs = {
            'user_prompt': query,
            'session_id': session_id,
        }
        logger.info(f'Inputs {inputs}')
        print(f'Inputs {inputs}')
        response = self.itinerary_crew.kickoff(inputs)
        return response

    async def stream(self, query: str) -> AsyncIterable[dict[str, Any]]:
        """Streaming is not supported by CrewAI."""
        raise NotImplementedError('Streaming is not supported by CrewAI.')

    # def get_image_data(self, session_id: str, image_key: str) -> Imagedata:
    #     """Return Imagedata given a key. This is a helper method from the agent."""
    #     cache = InMemoryCache()
    #     session_data = cache.get(session_id)
    #     try:
    #         cache.get(session_id)
    #         return session_data[image_key]
    #     except KeyError:
    #         logger.error('Error generating image')
    #         return Imagedata(error='Error generating image, please try again.')
