from collections.abc import AsyncIterable
from typing import Any, Literal, Dict

import httpx

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from serpapi import GoogleSearch
import os 
from dotenv import load_dotenv
load_dotenv()

memory = MemorySaver()

def format_hotels_data(hotels_data):
    formatted_hotels = []

    for i, hotel in enumerate(hotels_data):
        name = hotel.get("name", "Unknown hotel")
        hotel_class = hotel.get("hotel_class", "Unrated")
        check_in = hotel.get("check_in_time", "Not specified")
        check_out = hotel.get("check_out_time", "Not specified")
        rate = hotel.get("rate_per_night", {}).get("lowest", "Unknown")
        total_rate = hotel.get("total_rate", {}).get("lowest", "Unknown")
        rating = hotel.get("overall_rating", "No rating")
        reviews = hotel.get("reviews", "No reviews")
        amenities = ", ".join(hotel.get("amenities", [])) or "No amenities listed"
        nearby = hotel.get("nearby_places", [])

        nearby_details = ""
        for place in nearby:
            place_name = place["name"]
            transports = "; ".join([f"{t['type']} ({t['duration']})" for t in place.get("transportations", [])])
            nearby_details += f"  - {place_name}: {transports}\n"

        hotel_str = (
            f"Hotel {i + 1} Information:\n"
            f"Hotel Name: {name}\n"
            f"Class: {hotel_class}\n"
            f"Overall Rating: {rating} ({reviews} reviews)\n"
            f"Check-in Time: {check_in} | Check-out Time: {check_out}\n"
            f"Rate per Night: {rate} | Total Stay Price: {total_rate}\n"
            f"Amenities: {amenities}\n"
        )

        if nearby_details:
            hotel_str += f"Nearby Places:\n{nearby_details}"

        formatted_hotels.append(hotel_str.strip())

    return formatted_hotels

@tool
def search_hotels(location: str, check_in_date: str, check_out_date: str):
    """
    Search for hotels based on user input.

    Args:
        location (str): The location to search for hotels.
        check_in_date (str): The check-in date.
        check_out_date (str): The check-out date.

    Returns:
        list: A list of hotel options.
    """
    params = {
        "engine": "google_hotels",
        "q": location,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "currency": "USD",
        "hl": "en",
        "gl": "us",
        "api_key": os.getenv('SERP_API_KEY'),
        "sort_by": 3,
        "rating": 8
    }

    search = GoogleSearch(params)
    hotels_data = search.get_dict().get("properties", [])
    return format_hotels_data(hotels_data)


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class HotelSearchAgent:
    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for hotel searches. '
        "Your sole purpose is to use the 'search_hotels' tool to answer questions about hotel availability and pricing. "
        'If the user asks about anything other than hotel searches, '
        'politely state that you cannot help with that topic and can only assist with hotel-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
        'Set response status to input_required if the user needs to provide more information.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __init__(self):
        self.model = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')
        self.tools = [search_hotels]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def invoke(self, query, sessionId) -> str:
        config = {'configurable': {'thread_id': sessionId}}
        self.graph.invoke({'messages': [('user', query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': sessionId}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the hotels...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the hotel search results..',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            elif structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            elif structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': 'We are unable to process your request at the moment. Please try again.',
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
