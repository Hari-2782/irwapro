import pandas as pd
import pickle
import requests
import sqlite3

# Function to fetch movie poster
def fetch_poster(movie_id):
    response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=020b311fe0559698373a16008dc6a672&language=en-US')
    data = response.json()
    return "https://image.tmdb.org/t/p/w500/" + data['poster_path']

# Function to recommend movies based on similarity
def recommend(movie_title, movies, similarity):
    movie_index = movies[movies['title'] == movie_title].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommended_movies_posters = []
    for x in movies_list:
        movie_id = movies.iloc[x[0]].movie_id
        recommended_movies.append(movies.iloc[x[0]].title)
        recommended_movies_posters.append(fetch_poster(movie_id))
    return recommended_movies, recommended_movies_posters

# Function to get recommendations based on user history
def recommend_based_on_history(user_id, conn, movies, similarity):
    watched_movie_ids = []
    c = conn.cursor()
    
    for row in c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,)):
        watched_movie_ids.append(row[0])
    
    if not watched_movie_ids:
        return [], []

    recommended_movies, recommended_movies_posters = [], []
    for movie_id in watched_movie_ids:
        if movie_id in movies['movie_id'].values:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            names, posters = recommend(movie_title, movies, similarity)
            recommended_movies.extend(names)
            recommended_movies_posters.extend(posters)

    return recommended_movies[:5], recommended_movies_posters[:5]

# Function to add user rating
def add_rating(user_id, movie_id, rating, conn):
    c = conn.cursor()
    c.execute("INSERT INTO ratings (user_id, movie_id, rating) VALUES (?, ?, ?)", (user_id, movie_id, rating))
    conn.commit()
