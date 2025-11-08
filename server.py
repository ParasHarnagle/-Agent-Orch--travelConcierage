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
app = FastMCP("sentient-roadtrip-mcp")
# -----------------------------------------------------
#  1. Mood Analyzer
# -----------------------------------------------------
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


# -----------------------------------------------------
#  2. Route Planner (Google Directions API)
# -----------------------------------------------------
@app.tool()
def plan_route(input: dict):
    print("planning route ...")
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

    if not resp.get("routes"):
        return {"error": "Unable to find route"}

    leg = resp["routes"][0]["legs"][0]

    return {
        "origin": origin,
        "destination": destination,
        "distance_km": leg["distance"]["value"] / 1000,
        "duration_hours": leg["duration"]["value"] / 3600,
        "start_location": leg["start_location"],
        "end_location": leg["end_location"],
       # "polyline": resp["routes"][0]["overview_polyline"]["points"]
    }
# -----------------------------------------------------
#  3. Fuel Cost Estimator
# -----------------------------------------------------
@app.tool()
def estimate_fuel_cost(input: dict):
    print("estimating fuel cost....")
    dist = input["distance_km"]
    mileage = input.get("mileage_kmpl", 18)
    price = input.get("fuel_price", 110)

    liters = dist / mileage
    cost = liters * price

    return {
        "distance_km": dist,
        "liters_required": round(liters, 2),
        "total_cost": round(cost, 2)
    }

# -----------------------------------------------------
#  4. Scenic Spots (Google Places API)
# -----------------------------------------------------
@app.tool()
def find_scenic_spots(input: dict):
    print("finding scenic stops on the way...")
    lat = input["lat"]
    lng = input["lng"]
    radius = input.get("radius", 8000)

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": "scenic viewpoint OR waterfall OR lake OR forest",
        "key": GOOGLE_MAPS_API_KEY
    }

    return httpx.get(url, params=params).json()

# -----------------------------------------------------
#  5. Food / Rest Stops (Google Places API)
# -----------------------------------------------------
@app.tool()
def find_food_rest_stops(input: dict):
    print("finding something to eat...")
    lat = input["lat"]
    lng = input["lng"]

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 2000,
        "keyword": "highway cafe OR dhaba OR restaurant OR tea stall",
        "key": GOOGLE_MAPS_API_KEY
    }

    return httpx.get(url, params=params).json()

# -----------------------------------------------------
#  6. Weather (Open-Meteo, free)
# -----------------------------------------------------
@app.tool()
def get_weather_on_route(input: dict):
    print("clothes to bring....")
    lat = input["lat"]
    lng = input["lng"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,weather_code"
    }

    return httpx.get(url, params=params).json()

# -----------------------------------------------------
#  7. Image Search (DuckDuckGo, free)
# -----------------------------------------------------
#@app.tool()
def search_images(input: dict):
    print("searching for images ....")
    query = input["query"]

    try:
        resp = httpx.get(
            "https://duckduckgo.com/i.js",
            params={"q": query},
            timeout=10
        ).json()

        results = [
            {"title": r.get("title"), "url": r.get("image")}
            for r in resp.get("results", [])[:2]
        ]

        return {"query": query, "images": results}

    except Exception as e:
        return {"error": str(e)}
    
# -----------------------------------------------------
#  8. Trip Memory Image Generator (Pollinations SDXL)
# -----------------------------------------------------
@app.tool()
def generate_trip_media(input: dict):
    print("generating trip media...")
    destination = input["destination"]
    style = input.get("style", "cinematic landscape")

    cse_params = {
        "key": GOOGLE_CSE_KEY,
        "cx": GOOGLE_CSE_ID,
        "searchType": "image",
        "q": destination,
        "num": 1,
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
        #"raw_cse_response": cse_raw
    }
# -----------------------------------------------------
#  9. Itinerary Generator
# -----------------------------------------------------
@app.tool()
def generate_roadtrip_itinerary(input: dict):
    print("generating the plan...")
    dest = input["destination"]
    days = input.get("days", 2)
    vibe = input.get("vibe", "scenic")

    it = []
    for d in range(days):
        it.append({
            "day": d + 1,
            "theme": vibe,
            "morning": f"Drive towards {dest} through peaceful roads.",
            "afternoon": "Stop at notable scenic points.",
            "evening": f"Enjoy sunset overlooking {dest}."
        })

    return {"destination": dest, "itinerary": it}


# -----------------------------------------------------
#  10. Context Enhancer
# -----------------------------------------------------
@app.tool()
def enhance_destination_context(input: dict):
    print("Final enhancements going on....")
    dest = input["destination"]

    return {
        "destination": dest,
        "best_months": ["Oct", "Nov", "Dec", "Jan"],
        "local_food": ["local thali", "filter coffee"],
        "hidden_gems": ["Secret viewpoint", "Forest trail"],
        "warnings": ["Fog in early mornings", "Refuel before remote roads"]
    }

async def main():
    await app.run_async(transport="http", port=5003)

if __name__ == "__main__":
    asyncio.run(main())