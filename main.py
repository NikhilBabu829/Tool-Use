import httpx
from rich import print, console
from dotenv import load_dotenv
import json
import os

con = console.Console()

load_dotenv()

def get_geo_location(input : str):
    with httpx.Client() as client:
        response = client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={input}&count=1&language=en&format=json")
        if response.status_code == 200:
            the_response = response.json()
            results = the_response.get("results")[0]
            latitude = results.get("latitude")
            longitude = results.get("longitude")
            con.log(f"Latitude = {latitude}")
            con.log(f"longitude = {longitude}")
            return latitude, longitude

def get_current_weather(input : str, tool_id):
    con.log(f"Location given is {input}")
    con.log("Getting the coords for the location given")
    latitude, longitude = get_geo_location(input)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    with httpx.Client() as client:
        response = client.get(url=url)
        if(response.status_code == 200):
            response = response.json()
            to_return = {
                "role" : "user",
                "content" : [
                    {
                        "type" : "tool_result", 
                        "tool_use_id" : f"{tool_id}", 
                        "content" : json.dumps(response)
                    }
                ]
            }
            return to_return

def contact_ai():
    url = "https://api.anthropic.com/v1/messages"
    model = "claude-haiku-4-5-20251001"
    headers = {
        "x-api-key": os.getenv("CLAUDE_KEY"),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload ={
        "model" : model,
        "max_tokens": 500,
        "tools" : [
            {
                "name" : "get_current_weather",
                "description" : "Get the current weather for a given location",
                "input_schema" : {
                    "type" : "object",
                    "properties" : {
                        "location" : {
                            "type" : "string",
                            "description" : "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required" : ["location"]
                }
            }
        ],
        "tool_choice" : {"type" : "auto"},
        "messages" : [
            {
                "role" : "user",
                "content" : "What is the current weather of Dublin, Ireland?"
            }
        ]
    }
    with httpx.Client() as client:
        while True:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                response_data = response.json()
                stop_reason = response_data.get("stop_reason")
                tools = response_data.get("content")
                payload["messages"].append({
                    "role" : response_data["role"],
                    "content" : response_data["content"]
                })
                if(stop_reason == "tool_use"):
                    for tool in tools:
                        if(tool.get("name") == "get_current_weather"):
                            responseFromWeatherAPI = get_current_weather(tool.get("input").get("location"), tool_id=tool.get("id"))
                            payload["messages"].append(responseFromWeatherAPI)
                else:
                    con.log("Now inside the else meaning tool_use is not avl")
                    stop_reason = response_data.get("stop_reason")
                    response_data = response.json()
                    if(stop_reason != "tool_use"):
                        print(response_data)
                        break
                    raise Exception("The AI did not respond with a valid end_turn stop reason.")
            else:
                print(f"Error: {response.status_code} - {response.text}")

def main():
    contact_ai()
    
if __name__ == "__main__":
    main()
