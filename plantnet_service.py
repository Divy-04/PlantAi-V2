import os
import requests
from dotenv import load_dotenv

load_dotenv()

PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "")
PLANTNET_URL     = "https://my-api.plantnet.org/v2/identify/all"

# If PlantNet score is below this, we reject the image as "not a plant"
MIN_PLANT_SCORE = 0.10


def identify_plant(image_bytes: bytes) -> dict:
    """
    Sends image to PlantNet API.

    Returns:
        {
            "is_plant":     bool,
            "common_name":  str,   # e.g. "Tomato"
            "species":      str,   # e.g. "Solanum lycopersicum"
            "score":        float, # PlantNet confidence 0.0–1.0
            "family":       str,   # e.g. "Solanaceae"
        }

    Raises:
        RuntimeError if API key is missing or request fails badly.
    """

    if not PLANTNET_API_KEY:
        # If no API key is configured, skip PlantNet gracefully
        # — disease model will still run, plant info will be empty
        return {
            "verified":    False,
            "is_plant":    True,
            "common_name": "",
            "species":     "",
            "score":       1.0,
            "family":      "",
        }

    try:
        response = requests.post(
            PLANTNET_URL,
            params  = {"api-key": PLANTNET_API_KEY, "lang": "en"},
            files   = {"images": ("plant.jpg", image_bytes, "image/jpeg")},
            timeout = 20,
        )
    except requests.exceptions.Timeout:
        # PlantNet timed out — don't block the user, just skip plant info
        return {
            "verified":    False,
            "is_plant":    True,
            "common_name": "",
            "species":     "",
            "score":       1.0,
            "family":      "",
        }
    except requests.exceptions.RequestException as e:
        print(f"PlantNet request failed, skipping plant lookup: {e}")
        return {
            "verified":    False,
            "is_plant":    True,
            "common_name": "",
            "species":     "",
            "score":       1.0,
            "family":      "",
        }

    # 404 from PlantNet = no plant matched at all
    if response.status_code == 404:
        return {
            "verified":    True,
            "is_plant":    False,
            "common_name": "",
            "species":     "",
            "score":       0.0,
            "family":      "",
        }

    if not response.ok:
        # Other errors — skip PlantNet, don't block user
        return {
            "verified":    False,
            "is_plant":    True,
            "common_name": "",
            "species":     "",
            "score":       1.0,
            "family":      "",
        }

    data    = response.json()
    results = data.get("results", [])

    if not results:
        return {
            "verified":    True,
            "is_plant":    False,
            "common_name": "",
            "species":     "",
            "score":       0.0,
            "family":      "",
        }

    top     = results[0]
    score   = float(top.get("score", 0.0))

    # Below threshold = not a plant (or too unclear to be useful)
    if score < MIN_PLANT_SCORE:
        return {
            "verified":    True,
            "is_plant":    False,
            "common_name": "",
            "species":     "",
            "score":       round(score, 4),
            "family":      "",
        }

    species_info  = top.get("species", {})
    common_names  = species_info.get("commonNames", [])
    common_name   = common_names[0].title() if common_names else ""
    species_name  = species_info.get("scientificNameWithoutAuthor", "")
    family_name   = species_info.get("family", {}).get("scientificNameWithoutAuthor", "")

    return {
        "verified":    True,
        "is_plant":    True,
        "common_name": common_name,
        "species":     species_name,
        "score":       round(score, 4),
        "family":      family_name,
    }
