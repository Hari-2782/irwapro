import pandas as pd
import streamlit as st
import pickle
import requests
import time
import sqlite3
import bcrypt
import numpy as np
import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Retrieve the OpenAI API key from the environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create a connection to the database
conn = sqlite3.connect('movie_recommendation.db', check_same_thread=False)
c = conn.cursor()
# Function to fetch movie poster
def fetch_poster(movie_id):
    response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=020b311fe0559698373a16008dc6a672&language=en-US')
    data = response.json()
    return "https://image.tmdb.org/t/p/w500/" + data['poster_path']
def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommended_movies_posters = []
    for x in movies_list:
        movie_id = movies.iloc[x[0]].movie_id
        recommended_movies.append(movies.iloc[x[0]].title)
        recommended_movies_posters.append(fetch_poster(movie_id))
    return recommended_movies, recommended_movies_posters
# Function to recommend movies based on user history
def recommend_based_on_history(user_id):
    watched_movie_ids = [row[0] for row in c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,))]
    if not watched_movie_ids:
        return [], []

    recommended_movies, recommended_movies_posters = [], []
    for movie_id in watched_movie_ids:
        if movie_id in movies['movie_id'].values:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            names, posters = recommend(movie_title)
            recommended_movies.extend(names)
            recommended_movies_posters.extend(posters)
            recommended_movies.extend(names[:2])
            recommended_movies_posters.extend(posters[:2])

    # return recommended_movies[:2], recommended_movies_posters[:2]
    return recommended_movies, recommended_movies_posters

# Function to authenticate user

# Function to add a movie to the user's watch history
def add_to_watch_history(user_id, movie_title):
    movie_id = movies[movies['title'] == movie_title].iloc[0].movie_id
    try:
        c.execute("INSERT INTO watch_history (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Function to handle hybrid recommendation (content + collaborative)
def hybrid_recommend(movie_title, user_id):
    recommended_movies, recommended_movies_posters = recommend(movie_title)
    watched_movies = [row[0] for row in c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,))]
    
    if watched_movies:
        additional_recommendations, additional_posters = recommend_based_on_history(user_id)
        combined_recommendations = list(set(recommended_movies + additional_recommendations))
        combined_posters = list(set(recommended_movies_posters + additional_posters))
        return combined_recommendations[:5], combined_posters[:5]
    
    return recommended_movies, recommended_movies_posters

# Function to use ChatGPT for movie recommendations
def chatgpt_recommend(query):
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Use the GPT-4 model
        messages=[
            {"role": "user", "content": f"Recommend a movie based on the following query: {query}"}
        ],
        max_tokens=150
    )
    return response.choices[0].message['content'].strip()  # Access content differently for chat models


movies_dict = pickle.load(open('movie_dict_4.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open('similarity_4.pkl', 'rb'))
# Streamlit UI
st.title("Bala Cinema - Movie Recommendation System")
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Login", "Movies", "Search", "ChatBot", "Logout"])

# Session management
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Login/Register functionality
if page == "Login":
    auth_choice = st.selectbox("Login or Register", ["Login", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
    
    if auth_choice == "Register" and st.button("Register"):
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            st.success("Registration successful!")
        except sqlite3.IntegrityError:
            st.error("Username already exists!")
    elif auth_choice == "Login" and st.button("Login"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2]):
            st.session_state.user_id = user[0]
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")

# Movie recommendations page
elif page == "Movies" and st.session_state.user_id:
    st.write("Welcome to the Movies page!")
    st.write("Your personalized recommendations:")
    
    names, posters = recommend_based_on_history(st.session_state.user_id)
    if names:
        for name, poster in zip(names, posters):
            st.image(poster, width=150)
            st.write(f"**{name}**")
    else:
        st.write("No recommendations. Add movies to your watch history.")

    

# Search recommendations page
elif page == "Search" and st.session_state.user_id  :
    st.write("Search for movie recommendations:")
    selected_movie = st.selectbox('Search and add a movie to your watch history:', movies['title'].values)
    if st.button("Add to Watch History"):
        if add_to_watch_history(st.session_state.user_id, selected_movie):
            st.success(f"{selected_movie} added!")
        else:
            st.error(f"{selected_movie} is already in your watch history.")
    if st.button("Search"):
        names, posters = hybrid_recommend(selected_movie, st.session_state.user_id)
        for name, poster in zip(names, posters):
            st.image(poster, width=150)
            st.write(f"**{name}**")

# ChatBot page
elif page == "ChatBot" and st.session_state.user_id:
    st.write("Chat with our movie recommendation bot!")
    
    user_query = st.text_input("Ask for a movie recommendation:")
    if st.button("Ask"):
        chatgpt_response = chatgpt_recommend(user_query)
        st.write(f"**ChatGPT recommends:** {chatgpt_response}")

# Logout page
elif page == "Logout" and st.session_state.user_id:
    st.session_state.user_id = None
    st.success("You have been logged out.")

if not st.session_state.user_id and page != "Login":
    st.warning("Please log in to access this page.")
