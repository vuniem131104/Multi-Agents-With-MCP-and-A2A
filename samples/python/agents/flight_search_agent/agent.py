from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from typing import Any, AsyncIterable
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class FlightSearchAgent:
    """An agent that handles flight search requests."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = 'remote_agent'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return 'Processing the flight search request...'

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the flight search agent."""
        return LlmAgent(
            model='gemini-2.0-flash',
            name='flight_search_agent',
            description=(
                'This agent handles the flight search process for users.'
            ),
            instruction = """
You are a flight search agent. Your task is to assist users in finding flights, hotels, and other travel-related services. You will interact with the user to gather necessary information and provide relevant options based on their requests.

When handling flight-related queries, extract the following key information:
- Departure airport code
- Arrival airport code
- Departure date
- Return date (if mentioned)

Guidelines:
1. If the user provides a location in the format "City Name (XXX)", extract only the IATA airport code (e.g., "Hanoi (HAN)" → "HAN").
2. All dates must be converted to the standard format "yyyy-mm-dd".
3. If the user gives a relative date (e.g., "next Friday", "tomorrow", "July 5th"), convert it to "yyyy-mm-dd" format based on today’s date.
4. You do not need to return data in JSON. Instead, generate a clean and concise sentence in English with the extracted details, such as:
   - "From HAN to NRT, departing on 2025-06-15, returning on 2025-06-22."
   - "From SGN to CDG, departing on 2025-07-10."

Keep your responses brief and focused, ready to be passed to a downstream tool.
""",
            tools=[
                MCPToolset(
                    connection_params=StdioServerParameters(
                        command="uv",
                        args=["--directory", "/home/vuiem/Flight-Recommendation/mcp_server", "run", "server.py"],
                    ),
                    tool_filter=['search_flights']
                )
            ],
        )

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ''
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = '\n'.join(
                        [p.text for p in event.content.parts if p.text]
                    )
                elif (
                    event.content
                    and event.content.parts
                    and any(
                        [
                            True
                            for p in event.content.parts
                            if p.function_response
                        ]
                    )
                ):
                    response = next(
                        p.function_response.model_dump()
                        for p in event.content.parts
                    )
                yield {
                    'is_task_complete': True,
                    'content': response,
                }
            else:
                yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                }

# if __name__ == '__main__':

#     agent = FlightSearchAgent()
#     llm = agent._build_agent()