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



# A simple in-memory cache (replace with a file/db if you want persistence)
LAST_KNOWN = {
    'avg_rent_2bed': None,
    'avg_price_2bed': None
}

def avg_housing_cost(place):
    url = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    headers = {
        "X-RapidAPI-Key": os.environ.get("ZILLOW_RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
    }
    params = {
        "location": place,
        "propertyType": "2-bedroom"
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        print("Zillow API response:", data)

        # Adjust these keys based on your actual API response structure
        avg_rent = data.get("rent", {}).get("average")
        avg_price = data.get("price", {}).get("average")

        # If either is missing, fallback to last known
        if avg_rent is None:
            avg_rent = LAST_KNOWN['avg_rent_2bed']
        else:
            LAST_KNOWN['avg_rent_2bed'] = avg_rent

        if avg_price is None:
            avg_price = LAST_KNOWN['avg_price_2bed']
        else:
            LAST_KNOWN['avg_price_2bed'] = avg_price

        # Round values for nicer display: to nearest $1,000 for rent, $10,000 for price
        def nice_round(val, base):
            if val is None:
                return "N/A"
            return f"${int(round(val / base) * base):,}"

        return {
            'avg_rent_2bed': nice_round(avg_rent, 1000),
            'avg_price_2bed': nice_round(avg_price, 10000)
        }
    except Exception as e:
        print("Error in avg_housing_cost:", e)
        # Fallback to last known if available
        def nice_round(val, base):
            if val is None:
                return "N/A"
            return f"${int(round(val / base) * base):,}"
        return {
            'avg_rent_2bed': nice_round(LAST_KNOWN['avg_rent_2bed'], 1000),
            'avg_price_2bed': nice_round(LAST_KNOWN['avg_price_2bed'], 10000)
        }

def crime_rate(place):
    return random.choice(['Low', 'Medium', 'High'])

def commute_score(place):
    score = random.randint(1, 10)
    mode = random.choice(["car", "train", "bus", "bike", "walk"])
    return score, mode

def walkability_score(lat, lon):
    return random.randint(1, 100)

def diversity_index(place):
    return round(random.uniform(0.3, 0.9), 2)

def pet_score(green_count, walk_score):
    return round((green_count * 10 + walk_score) / 2)

def parking_score(lat, lon):
    parks = get_nearby_places(lat, lon, 'amenity=parking', 'parking')
    return len(parks)

def get_all_metrics(place, lat, lon):
    housing = avg_housing_cost(place)
    crime = crime_rate(place)
    schools = get_nearby_places(lat, lon, 'amenity=school', 'schools') + get_nearby_places(lat, lon, 'amenity=college', 'colleges')
    schools_with_ratings = [f"{school} (Rating: {random.randint(1,10)}/10)" for school in schools]
    commute_sc, commute_type = commute_score(place)
    parks = get_nearby_places(lat, lon, 'leisure=park', 'parks')
    walk_sc = walkability_score(lat, lon)
    gyms = get_nearby_places(lat, lon, 'leisure=fitness_centre', 'gyms')
    shopping = get_nearby_places(lat, lon, 'shop', 'shopping')
    hospitals = get_nearby_places(lat, lon, 'amenity=hospital', 'hospitals')
    parking_ct = parking_score(lat, lon)
    div_ix = diversity_index(place)
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
        "Diversity Index": div_ix,
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
