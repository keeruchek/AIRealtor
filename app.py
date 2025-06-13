import streamlit as st
import os
import requests
import pandas as pd
import random
from web_agent import ask_web_ai  # new import for AI

# 🗺️ Geocoding using OpenCage Geocoder
def geocode_location(place_name):
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {'q': place_name, 'key': '8e8875148f2f42e791dd420015550342', 'limit': 1}
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get('results'):
            geo = resp['results'][0]['geometry']
            return geo['lat'], geo['lng']
    except:
        pass
    return None, None

# Updated Nearby places via Overpass API
def get_nearby_places(lat, lon, query, label, radius=2000):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node[{query}](around:{radius},{lat},{lon});
      way[{query}](around:{radius},{lat},{lon});
      relation[{query}](around:{radius},{lat},{lon});
    );
    out center;
    """
    try:
        response = requests.post(url, data={"data": query}, timeout=15)
        data = response.json()
        places = []
        for element in data.get("elements", []):
            name = element.get("tags", {}).get("name")
            if name:
                places.append(name)
        return places[:10] if places else [f"No {label} found"]
    except Exception as e:
        return [f"Error fetching {label}: {e}"]


def avg_housing_cost(place):
    avg_rent_2bed = random.randint(1500, 3500)
    avg_price_2bed = random.randint(250000, 750000)
    return {
        'avg_rent_2bed': f"${avg_rent_2bed:,}",
        'avg_price_2bed': f"${avg_price_2bed:,}"
    }

def crime_rate(place):
    return random.choice(['Low', 'Medium', 'High'])

def commute_score(lat, lon, destination_lat, destination_lon):
    api_key = os.environ.get("ORS_API_KEY")
    url = f"https://api.openrouteservice.org/v2/directions/driving-car"
    params = {
        "api_key": api_key,
        "start": f"{lon},{lat}",
        "end": f"{destination_lon},{destination_lat}"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        duration = data['features'][0]['properties']['summary']['duration'] // 60  # minutes
        # Score: invert duration, you can calibrate this
        score = max(1, 10 - int(duration // 10))
        mode = "car"
        return score, mode
    except Exception as e:
        print("Commute Score API error:", e)
        return "N/A", "N/A"

def walkability_score(lat, lon):
    parks = get_nearby_places(lat, lon, 'leisure=park', 'parks')
    shops = get_nearby_places(lat, lon, 'shop', 'shops')
    schools = get_nearby_places(lat, lon, 'amenity=school', 'schools')
    # Simple formula: more amenities = higher score (scale to 100)
    score = min(100, (len(parks) + len(shops) + len(schools)) * 5)
    return score

def get_school_rating(school_name, lat, lon):
    url = "https://api.schooldigger.com/v1.2/schools"
    params = {"school": school_name, "lat": lat, "lon": lon}  # adjust as needed
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        # Adjust according to your actual API response structure
        return data.get("rating", "N/A")
    except Exception as e:
        return "N/A"

def pet_score(green_count, walk_score):
    return round((green_count * 10 + walk_score) / 2)

def parking_score(lat, lon):
    parks = get_nearby_places(lat, lon, 'amenity=parking', 'parking')
    return len(parks)

def get_all_metrics(place, lat, lon):
    housing = avg_housing_cost(place)
    crime = crime_rate(place)
    schools_with_ratings = [
    f"{school} (Rating: {get_school_rating(school, lat, lon)}/10)" for school in schools
    ]
    # Choose your destination for commute scoring (example: Downtown Boston)
    destination = "Downtown Boston, MA"
    destination_lat, destination_lon = geocode_location(destination)
    commute_sc, commute_type = commute_score(lat, lon, destination_lat, destination_lon)
    parks = get_nearby_places(lat, lon, 'leisure=park', 'parks')
    walk_sc = walkability_score(lat, lon)
    gyms = get_nearby_places(lat, lon, 'leisure=fitness_centre', 'gyms')
    shopping = get_nearby_places(lat, lon, 'shop', 'shopping')
    hospitals = get_nearby_places(lat, lon, 'amenity=hospital', 'hospitals')
    parking_ct = parking_score(lat, lon)
    
    pet_sc = pet_score(len(parks), walk_sc)

    return {
        "Average Rent (2 bed)": housing['avg_rent_2bed'],
        "Average Sale Price (2 bed)": housing['avg_price_2bed'],
        "Crime Rate": crime,
        "Schools Nearby": schools_with_ratings,
        "Commute Score": commute_sc,
        "Transit Type": commute_type,
        "Green Space (parks count)": len(parks),
        "Walkability Score": walk_sc,
        "Gyms Nearby": gyms,
        "Shopping Nearby": shopping,
        "Hospitals Nearby": hospitals,
        "Parking Score (count)": parking_ct,
        "PET Score": pet_sc
    }

# ============ Streamlit UI Setup ============

st.set_page_config(page_title="Neighborhood Insights", layout="centered")
st.title("Where to live next?")

mode = st.radio("Mode:", ("Compare Two Places", "Single Place"))
place1 = st.text_input("Place 1 (City, State)", "Cambridge, MA")
place2 = st.text_input("Place 2 (City, State)", "Somerville, MA") if mode == "Compare Two Places" else None

# --- Session state for insights/results ---
if "insights_data" not in st.session_state:
    st.session_state["insights_data"] = None
if "map_data" not in st.session_state:
    st.session_state["map_data"] = None
if "places" not in st.session_state:
    st.session_state["places"] = None
if "ai_answer" not in st.session_state:
    st.session_state["ai_answer"] = None
if "ai_error" not in st.session_state:
    st.session_state["ai_error"] = None

if st.button("Show Insights"):
    lat1, lon1 = geocode_location(place1)
    lat2, lon2 = (None, None)
    if mode == "Compare Two Places":
        lat2, lon2 = geocode_location(place2)

    if lat1 is None:
        st.error(f"Couldn't locate {place1}")
        st.stop()
    if mode == "Compare Two Places" and lat2 is None:
        st.error(f"Couldn't locate {place2}")
        st.stop()

    locs = [{'lat': lat1,'lon':lon1,'place':place1}]
    if mode == "Compare Two Places":
        locs.append({'lat':lat2,'lon':lon2,'place':place2})

    data1 = get_all_metrics(place1, lat1, lon1)
    data2 = get_all_metrics(place2, lat2, lon2) if mode=="Compare Two Places" else None

    # STORE all results in session_state
    st.session_state["places"] = (place1, place2)
    st.session_state["map_data"] = locs
    st.session_state["insights_data"] = (data1, data2, mode)
    # Clear AI answer if new insights shown
    st.session_state["ai_answer"] = None
    st.session_state["ai_error"] = None

# ---- Always display results if available ----

if st.session_state["insights_data"]:
    data1, data2, mode = st.session_state["insights_data"]
    place1, place2 = st.session_state["places"]
    locs = st.session_state["map_data"]
    st.map(pd.DataFrame(locs))

    if mode=="Compare Two Places":
        col1, col2 = st.columns(2)
        for col, place, data in [(col1, place1, data1), (col2, place2, data2)]:
            with col:
                st.subheader(place)
                for k,v in data.items():
                    if isinstance(v, list):
                        st.markdown(f"**{k}:**")
                        for item in v:
                            st.markdown(f"- {item}")
                    else:
                        st.markdown(f"**{k}:** {v}")
    else:
        st.subheader(place1)
        for k,v in data1.items():
            if isinstance(v, list):
                st.markdown(f"**{k}:**")
                for item in v:
                    st.markdown(f"- {item}")
            else:
                st.markdown(f"**{k}:** {v}")

    
    # --- AI Chatbot Section ---
with st.container():
    st.markdown("---")
    st.subheader("🧠 AI Chatbot with Web Search")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask me anything:", key="user_input")

    if user_input:
        with st.spinner("Thinking..."):
            from web_agent import ask_web_ai
            response = ask_web_ai(user_input)
        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("AI", response))

    for speaker, msg in st.session_state.chat_history:
        st.markdown(f"**{speaker}:** {msg}")
