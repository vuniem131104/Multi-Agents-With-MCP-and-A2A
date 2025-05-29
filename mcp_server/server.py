from mcp.server.fastmcp import FastMCP 
from serpapi import GoogleSearch
import os 
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel 
from typing import Optional, List
load_dotenv()

class FlightRequest(BaseModel):
    from_location: str
    to_location: str
    check_in_date: str
    check_out_date: str

class HotelRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str

class AIResponse(BaseModel):
    flights: List[str] = []
    hotels: List[str] = []
    ai_flight_recommendations: Optional[str] = ""
    ai_hotel_recommendations: Optional[str] = ""
    
def format_flights_data(flights_data):
    formatted_flights = []

    for i, item in enumerate(flights_data):
        flight = item["flights"][0]  # Each item contains one flight
        dep = flight["departure_airport"]
        arr = flight["arrival_airport"]

        # Format departure and arrival time
        dep_time = datetime.strptime(dep["time"], "%Y-%m-%d %H:%M").strftime("%A, %d %B %Y at %H:%M")
        arr_time = datetime.strptime(arr["time"], "%Y-%m-%d %H:%M").strftime("%A, %d %B %Y at %H:%M")

        # Format CO2 emissions (convert grams to kilograms)
        co2_emissions = item["carbon_emissions"]["this_flight"] // 1000

        # Build the flight description
        description = (
            f"Flight {i + 1} Information:\n"
            f"Flight Number: {flight['flight_number']}\n"
            f"Airline: {flight['airline']}\n"
            f"Aircraft: {flight['airplane']}\n"
            f"Travel Class: {flight['travel_class']}\n"
            f"Departure Airport: {dep['name']} ({dep['id']})\n"
            f"Departure Time: {dep_time}\n"
            f"Arrival Airport: {arr['name']} ({arr['id']})\n"
            f"Arrival Time: {arr_time}\n"
            f"Duration: {flight['duration']} minutes\n"
            f"Legroom: {flight.get('legroom', 'Not specified')}\n"
            f"Carbon Emissions Estimate: {co2_emissions} kg\n"
            f"Ticket Price: ${item['price']}\n"
        )

        # Add extra features if any
        if "extensions" in flight:
            description += "Additional Features:\n"
            for ext in flight["extensions"]:
                description += f"  - {ext}\n"

        formatted_flights.append(description.strip())

    return formatted_flights

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


mcp = FastMCP(name="Travel Assistant", version="1.0.0")

@mcp.tool()
async def search_flights(from_location: str, to_location: str, check_in_date: str, check_out_date: str):
    """Search for flights based on user input.

    Args:
        from_location (str): The departure location.
        to_location (str): The arrival location.
        check_in_date (str): The check-in date.
        check_out_date (str): The check-out date.

    Returns:
        list: A list of flight options.
    """
    params = {
        "engine": "google_flights",
        "departure_id": from_location,
        "arrival_id": to_location,
        "outbound_date": check_in_date,
        "return_date": check_out_date,
        "currency": "USD",
        "hl": "en",
        "gl": "us",
        "api_key": os.getenv('SERP_API_KEY'),
    }

    search = GoogleSearch(params)
    flights_data = search.get_dict().get("best_flights", [])
    return format_flights_data(flights_data)

@mcp.tool()
async def search_hotels(location: str, check_in_date: str, check_out_date: str):
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

if __name__ == "__main__":
    
    mcp.run(transport='stdio')