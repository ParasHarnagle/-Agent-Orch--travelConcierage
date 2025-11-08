import os
import httpx
from dotenv import load_dotenv
load_dotenv()
import os
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv
import urllib.parse
import asyncio
load_dotenv()
# -----------------------------------------------------
#  ENV VARS
# -----------------------------------------------------
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
# Validate
if not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY missing in environment")


# -----------------------------------------------------
#  Create MCP Server
# -----------------------------------------------------
app = FastMCP("test-sentient-roadtrip-mcp")

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

@app.tool()
def analyze_roadtrip_mood(input: dict):
    print("analyzing sentiment..")
    mood = input.get("mood", "").lower()

    mapping = {
        "refresh": ["quiet", "forest", "calm"],
        "heartbreak": ["healing", "mountains", "solitude"],
        "adventure": ["thrill", "offroad"],
        "friends": ["fun", "nightlife"],
        "family": ["safe", "comfortable"],
        "luxury": ["premium", "smooth"],
    }

    persona_map = {
        "refresh": "Quiet Explorer",
        "heartbreak": "Healing Wanderer",
        "adventure": "Trail Seeker",
        "friends": "Social Voyager",
        "family": "Comfort Guardian",
        "luxury": "Premium Traveller",
    }

    return {
        "mood": mood,
        "persona": persona_map.get(mood, "Roadtrip Soul"),
        "vibes": mapping.get(mood, ["scenic"])
    }


def plan_route(input: dict):
    origin = input["origin"]
    destination = input["destination"]

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": GOOGLE_MAPS_API_KEY
    }

    resp = httpx.get(url, params=params).json()

    # For debugging: print full object
    print("RAW RESPONSE:\n", resp)

    if not resp.get("routes"):
        return {"error": resp.get("status", "Unable to find route")}

    leg = resp["routes"][0]["legs"][0]

    return {
        "origin": origin,
        "destination": destination,
        "distance_km": leg["distance"]["value"] / 1000,
        "duration_hours": leg["duration"]["value"] / 3600,
        "start_location": leg["start_location"],
        "end_location": leg["end_location"],
        #"polyline": resp["routes"][0]["overview_polyline"]["points"]
    }

def test_scenic_spots(lat, lng):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 8000,
        "keyword": "scenic viewpoint OR waterfall OR lake OR forest",
        "key": GOOGLE_MAPS_API_KEY
    }

    resp = httpx.get(url, params=params).json()
    return resp

def test_food_spots(lat, lng):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 8000,
        "keyword": "highway cafe OR dhaba OR restaurant OR tea stall",
        "key": GOOGLE_MAPS_API_KEY
    }

    resp = httpx.get(url, params=params).json()
    return resp

def test_weather(lat, lng):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,weather_code"
    }

    return httpx.get(url, params=params).json()


GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")

def search_images(input: dict):
    query = input["query"]

    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        "key": GOOGLE_CSE_KEY,
        "cx": GOOGLE_CSE_ID,
        "searchType": "image",
        "q": query,
        "num": 5,
        "safe": "active"
    }

    try:
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()

        if "items" not in data:
            return {
                "query": query,
                "images": [],
                "note": "No images found or quota exceeded.",
                "raw": data
            }

        images = [
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "thumbnail": item.get("image", {}).get("thumbnailLink"),
                "context": item.get("image", {}).get("contextLink")
            }
            for item in data["items"]
        ]

        return {"query": query, "images": images}

    except Exception as e:
        return {"error": str(e)}
    
def generate_trip_image(input: dict):
    destination = input["destination"]
    style = input.get("style", "cinematic landscape")

    prompt = (
        f"{destination} scenic road trip, cinematic, ultra detailed, "
        f"{style}, 4k HD"
    )
    safe = prompt.replace(" ", "%20")

    image_url = f"https://image.pollinations.ai/prompt/{safe}"

    return {
        "destination": destination,
        "style": style,
        "image_url": image_url
    }

import urllib.parse

def generate_trip_media(input: dict):
    destination = input["destination"]
    style = input.get("style", "cinematic landscape")

    # -------------------------------------------------
    # ✅ 1. Fetch Real Images from Google CSE
    # -------------------------------------------------
    cse_params = {
        "key": GOOGLE_CSE_KEY,
        "cx": GOOGLE_CSE_ID,
        "searchType": "image",
        "q": destination,
        "num": 5,
        "safe": "active"
    }

    cse_url = "https://www.googleapis.com/customsearch/v1"

    real_images = []
    cse_raw = None

    try:
        resp = httpx.get(cse_url, params=cse_params, timeout=10)
        cse_raw = resp.json()

        if "items" in cse_raw:
            real_images = [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "thumbnail": item.get("image", {}).get("thumbnailLink"),
                    "context": item.get("image", {}).get("contextLink")
                }
                for item in cse_raw["items"]
            ]
    except Exception as exc:
        cse_raw = {"error": str(exc)}

    # -------------------------------------------------
    # ✅ 2. Generate AI Cinematic Preview (Pollinations)
    # -------------------------------------------------
    ai_prompt = (
        f"{destination} scenic road trip, wide angle drone shot, "
        f"cinematic, ultra detailed, {style}, volumetric lighting, "
        f"atmospheric perspective, 4k HD"
    )

    encoded_prompt = urllib.parse.quote(ai_prompt)

    ai_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"

    print("AI URL---->",ai_image_url)
    return {
        "destination": destination,
        "style": style,
        "real_images": real_images,
        "ai_generated_preview": ai_image_url,
        "raw_cse_response": cse_raw
    }
async def main():
    await app.run_async(transport="http", port=5003)

if __name__ == "__main__":
    asyncio.run(main())

# if __name__ == "__main__":
#     # result = plan_route({
#     #     "origin": "Bangalore",
#     #     "destination": "Coorg"
#     # })

#     # # print("\nFINAL OUTPUT:\n", result)
#     # out = test_scenic_spots(13.3702, 77.6835)
#     # print(out)
#     # out = test_food_spots(13.3702, 77.6835)
#     # print(out)
#     print(generate_trip_media({
#     "destination": "Nandi Hills",
#     "style": "sunset golden hour"
# }))
#     #print(test_weather(13.3702, 77.6835))