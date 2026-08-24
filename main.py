import httpx
from rich import print, console
from dotenv import load_dotenv
import json
import os
import operator
from tavily import TavilyClient

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

def calculator(input : str, tool_id, a, b):
    operator_mapping = {
        "+" : operator.add,
        "-" : operator.sub,
        "*" : operator.mul,
        "/" : operator.truediv
    }

    if input in operator_mapping:
        action = operator_mapping[input]
        to_return = {
            "role" : "user",
            "content" : [
                {
                    "type" : "tool_result",
                    "tool_use_id" : f"{tool_id}",
                    "content" : f"{a} {input} {b} = {action(a,b)}"
                }
            ]
        }
        return to_return

def search_web(search_query : str, tool_id):
    tavily = TavilyClient(os.getenv("TAVILY_KEY"))
    response = tavily.search(search_query)
    print(response)

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
            },
            {
                "name" : "calculator",
                "description" : "solves math problems",
                "input_schema" : {
                    "type" : "object",
                    "properties" : {
                        "operator" : {
                            "type" : "string",
                            "description" : "The operator symbol for the math, e.g. +, -, *, /, ^"
                        },
                        "first_value" : {
                            "type" : "number",
                            "description" : "first value for the math operation"
                        },
                        "second_value" : {
                            "type" : "number",
                            "description" : "second value for the math operation"
                        }
                    },
                    "required" : ["operator", "first_value", "second_value"]
                }
            },
            {
                "name" : "web_search",
                "description" : "search the web / internet for answers",
                "input_schema" : {
                    "type" : "object",
                    "properties" : {
                        "search_query" : {
                            "type" : "string",
                            "description" : "query to search the web. e.g. search the current flights to India"
                        }
                    },
                    "required" : ["search_query"]
                }
            }
        ],
        "tool_choice" : {"type" : "auto"},
        "messages" : [
            {
                "role" : "user",
                "content" : "What are the next flights to India from Dublin"
            }
        ]
    }
    with httpx.Client() as client:
    # while True:
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
                    if(tool.get("name") == "calculator"):
                        responseFromCalculator = calculator(tool.get("input").get("operator"), tool_id=tool.get("id"), a=tool.get("input").get("first_value"), b=tool.get("input").get("second_value"))
                        payload["messages"].append(responseFromCalculator)
                    if(tool.get("name") == "web_search"):
                        print(response_data)
            else:
                con.log("Now inside the else meaning tool_use is not avl")
                stop_reason = response_data.get("stop_reason")
                response_data = response.json()
                if(stop_reason != "tool_use"):
                    print(response_data)
                    # break
                raise Exception("The AI did not respond with a valid end_turn stop reason.")
        else:
            print(f"Error: {response.status_code} - {response.text}")

responseFromAPI = {
    'model': 'claude-haiku-4-5-20251001',
    'id': 'msg_011CeMk2RPTrqKd749NRaR39',
    'type': 'message',
    'role': 'assistant',
    'content': [
        {
            'type': 'text',
            'text': "I'll search for information about the next flights from Dublin to India for you."
        },
        {
            'type': 'tool_use',
            'id': 'toolu_01WYjY7PgZQ7He7CQgZQ8j8g',
            'name': 'web_search',
            'input': {'search_query': 'next flights Dublin to India'},
            'caller': {'type': 'direct'}
        }
    ],
    'stop_reason': 'tool_use',
    'stop_sequence': None,
    'stop_details': None,
    'usage': {
        'input_tokens': 799,
        'cache_creation_input_tokens': 0,
        'cache_read_input_tokens': 0,
        'cache_creation': {
            'ephemeral_5m_input_tokens': 0,
            'ephemeral_1h_input_tokens': 0
        },
        'output_tokens': 76,
        'service_tier': 'standard',
        'inference_geo': 'not_available'
    }
}

def main():
    # contact_ai()
    tools = responseFromAPI["content"]
    for tool in tools:
        if tool.get("name") == "web_search":
            response = search_web(tool.get("input").get("search_query"), tool_id=tool.get("id"))
    
if __name__ == "__main__":
    main()
