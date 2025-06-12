import streamlit as st
import os
import requests
import pandas as pd
from web_agent import ask_web_ai  # new import for AI

# ... your existing geocode_location and get_all_metrics functions remain unchanged ...

# Set session state for button if not set yet
if "show_insights" not in st.session_state:
    st.session_state.show_insights = False

mode = st.radio("Choose Mode", ["Explore One Place", "Compare Two Places"])

# Place input UI
place1 = st.text_input("Place 1", "")
place2 = st.text_input("Place 2", "") if mode == "Compare Two Places" else ""
if st.button("Show Insights"):
    st.session_state.show_insights = True

# --- Show insights if flag is set ---
if st.session_state.show_insights:
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

    locs = [{'lat': lat1, 'lon': lon1, 'place': place1}]
    if mode == "Compare Two Places":
        locs.append({'lat': lat2, 'lon': lon2, 'place': place2})
    st.map(pd.DataFrame(locs))

    data1 = get_all_metrics(place1, lat1, lon1)
    data2 = get_all_metrics(place2, lat2, lon2) if mode == "Compare Two Places" else None

    if mode == "Compare Two Places":
        col1, col2 = st.columns(2)
        for col, place, data in [(col1, place1, data1), (col2, place2, data2)]:
            with col:
                st.subheader(place)
                for k, v in data.items():
                    if isinstance(v, list):
                        st.markdown(f"**{k}:**")
                        for item in v:
                            st.markdown(f"- {item}")
                    else:
                        st.markdown(f"**{k}:** {v}")
    else:
        st.subheader(place1)
        for k, v in data1.items():
            if isinstance(v, list):
                st.markdown(f"**{k}:**")
                for item in v:
                    st.markdown(f"- {item}")
            else:
                st.markdown(f"**{k}:** {v}")

    # --- AI Search Below Results ---
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
