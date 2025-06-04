"""This file serves as the main entry point for the application.

It initializes the A2A server, defines the agent's capabilities,
and starts the server to handle incoming requests.
"""

import logging
import os

import click

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import ItineraryGenerationAgent
from agent_executor import ItineraryGenerationAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

    pass


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
def main(host, port):
    """Entry point for the A2A + CrewAI Itinerary generation."""
    try:
        if not os.getenv('GROQ_API_KEY'):
            raise MissingAPIKeyError(
                'GROQ_API_KEY environment variable not set.'
            )

        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id='itinerary_generator',
            name='Itinerary Generator',
            description='Helps users create detailed travel itineraries based on their preferences and requirements.',
            tags=['generate itinerary', 'edit itinerary'],
            examples=['Create a master 2-week itinerary for a journey to Hanoi, Vietnam.',],
        )

        agent_card = AgentCard(
            name='Itinerary Generator Agent',
            description='This agent assists users in generating itineraries based on their preferences.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=ItineraryGenerationAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ItineraryGenerationAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        request_handler = DefaultRequestHandler(
            agent_executor=ItineraryGenerationAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )
        import uvicorn

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
