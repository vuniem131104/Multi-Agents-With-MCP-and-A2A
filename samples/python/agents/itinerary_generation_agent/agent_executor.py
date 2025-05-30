import json

from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import Event, EventQueue
from a2a.types import (
    InvalidParamsError,
    Part,
    Task,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    completed_task,
    new_artifact,
)
from a2a.utils.errors import ServerError
from agent import ItineraryGenerationAgent


class ItineraryGenerationAgentExecutor(AgentExecutor):
    """Itinerary Generation AgentExecutor Example."""

    def __init__(self):
        self.agent = ItineraryGenerationAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        try:
            result = self.agent.invoke(query, context.context_id)
            print(f'Final Result ===> {result}')
        except Exception as e:
            print('Error invoking agent: %s', e)
            raise ServerError(
                error=ValueError(f'Error invoking agent: {e}')
            ) from e

        event_queue.enqueue_event(
            completed_task(
                task_id=context.task_id,
                context_id=context.context_id,
                artifacts=[
                    new_artifact(
                        parts=[Part(root=TextPart(text=str(result.raw)))],
                        name='itinerary',
                    ),
                ],
                history=[context.message],
            )
        )

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    def _validate_request(self, context: RequestContext) -> bool:
        return False
