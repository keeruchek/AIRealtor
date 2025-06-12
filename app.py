import streamlit as st
import os
import requests
import pandas as pd
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

# Updated Nearby places via Overpass API (only this function changed)
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
    url = "https://your_zillow_api_url"
    headers = {"X-RapidAPI-Key": "d928b8efacmsh3ece55120b24756p168133jsnf6588ac12b1d"}
    params = {"location": place, "propertyType": "2-bedroom"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10).json()
        avg_rent = resp.get("rent", {}).get("average", "N/A")
        avg_price = resp.get("price", {}).get("average", "N/A")
        return {
            'avg_rent_2bed': f"${avg_rent:,}" if isinstance(avg_rent, (int, float)) else avg_rent,
            'avg_price_2bed': f"${avg_price:,}" if isinstance(avg_price, (int, float)) else avg_price
        }
    except Exception as e:
        return {'avg_rent_2bed': 'N/A', 'avg_price_2bed': 'N/A'}

def crime_rate(place):
    url = "https://your_zillow_api_url/crime"
    headers = {"X-RapidAPI-Key": "d928b8efacmsh3ece55120b24756p168133jsnf6588ac12b1d"}
    params = {"location": place}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10).json()
        # Adjust the field below as per your API’s response structure
        return resp.get("crime_level", "N/A")
    except Exception as e:
        return "N/A"

def commute_score(lat, lon):
    # Count public transit stops nearby as a proxy for score
    transit_places = get_nearby_places(lat, lon, 'public_transport=platform', 'public transit', radius=1000)
    score = min(len(transit_places), 10)  # Normalize to 0-10
    # Mode: just return 'transit' if more than 0 stops found
    mode = "transit" if score > 0 else "car"
    return score, mode

def walkability_score(lat, lon, radius=1000):
    # Define walkable amenities
    amenity_tags = [
        'amenity=restaurant', 'amenity=cafe', 'amenity=bar',
        'shop', 'amenity=pharmacy', 'amenity=bank',
        'leisure=park', 'amenity=school', 'amenity=library',
        'amenity=bus_station', 'amenity=theatre', 'amenity=cinema'
    ]
    total_count = 0
    for tag in amenity_tags:
        label = tag.split('=')[1] if '=' in tag else tag
        places = get_nearby_places(lat, lon, tag, label, radius)
        # Ignore error messages or not found
        places = [p for p in places if not p.startswith("No ") and not p.startswith("Error")]
        total_count += len(places)
    # Normalize to a 0-100 scale for walkability
    score = min(int(total_count * 2), 100)  # Adjust scaling as needed
    return score

def diversity_index(place):
    return round(random.uniform(0.3, 0.9), 2)

def pet_score(green_count, walk_score):
    return round((green_count * 10 + walk_score) / 2)

def parking_score(lat, lon):
    # Count nearby parking amenities
    parks = get_nearby_places(lat, lon, 'amenity=parking', 'parking')
    return len(parks)

def get_all_metrics(place, lat, lon):
    housing = avg_housing_cost(place)
    crime = crime_rate(place)
def get_school_data(lat, lon, radius=2):
    url = "https://api.schooldigger.com/v1.2/schools"
    params = {
        "st": "",  # optional: state abbreviation
        "lat": lat,
        "lon": lon,
        "distance": radius,
        "appID": "",  # Not needed for v1.2
        "appKey": "0568db1c7540e395bb773539fc1d7550"
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        schools = []
        for school in resp.get("schoolList", []):
            name = school.get("schoolName")
            rating = school.get("schoolRating", "N/A")
            schools.append(f"{name} (Rating: {rating}/10)")
        return schools
    except Exception as e:
        return ["N/A"]
    commute_sc, commute_type = commute_score(place)
    parks = get_nearby_places(lat, lon, 'leisure=park', 'parks')
    walk_sc = walkability_score(lat, lon)
    gyms = get_nearby_places(lat, lon, 'leisure=fitness_centre', 'gyms')
    shopping = get_nearby_places(lat, lon, 'shop', 'shopping')
    hospitals = get_nearby_places(lat, lon, 'amenity=hospital', 'hospitals')
    parking_ct = parking_score(lat, lon)
    div_ix = diversity_index(place)
    pet_sc = pet_score(walk_sc, len(parks))

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

# 🧭 Streamlit UI Setup
st.set_page_config(page_title="Neighborhood Insights", layout="centered")
st.title("Where to live next?")

mode = st.radio("Mode:", ("Compare Two Places", "Single Place"))
place1 = st.text_input("Place 1 (City, State)", "Cambridge, MA")
place2 = st.text_input("Place 2 (City, State)", "Somerville, MA") if mode == "Compare Two Places" else None

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

    # Show map
    locs = [{'lat': lat1,'lon':lon1,'place':place1}]
    if mode == "Compare Two Places":
        locs.append({'lat':lat2,'lon':lon2,'place':place2})
    st.map(pd.DataFrame(locs))

    data1 = get_all_metrics(place1, lat1, lon1)
    data2 = get_all_metrics(place2, lat2, lon2) if mode=="Compare Two Places" else None

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
