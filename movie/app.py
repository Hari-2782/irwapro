import pandas as pd
import streamlit as st
import pickle
import requests
import time
import sqlite3
import bcrypt

# Create a connection to the database
conn = sqlite3.connect('movie_recommendation.db', check_same_thread=False)
c = conn.cursor()

# Create users, watch_history, and ratings tables if they do not exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS watch_history (
                user_id INTEGER,
                movie_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id))''')

c.execute('''CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER,
                movie_id INTEGER,
                rating REAL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(movie_id) REFERENCES watch_history(movie_id))''')
conn.commit()

# Function to fetch movie poster
def fetch_poster(movie_id):
    response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=020b311fe0559698373a16008dc6a672&language=en-US')
    data = response.json()
    return "https://image.tmdb.org/t/p/w500/" + data['poster_path']
# Function to display table data in Streamlit
def display_table(table_name):
    query = f"SELECT * FROM {table_name}"
    data = pd.read_sql_query(query, conn)

    # Convert the columns to string with error handling
    for column in data.columns:
        data[column] = data[column].apply(lambda x: str(x).encode('utf-8', 'replace').decode('utf-8'))

    st.dataframe(data)

# Display users table
if st.button("Show Users Table"):
    display_table("users")

# Display watch history table
if st.button("Show Watch History Table"):
    display_table("watch_history")

# Display ratings table
if st.button("Show Ratings Table"):
    display_table("ratings")

# Function to recommend movies
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

# Function to get recommendations based on user history
def recommend_based_on_history(user_id):
    watched_movie_ids = []
    for row in c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,)):
        watched_movie_ids.append(row[0])

    if not watched_movie_ids:
        return [], []

    recommended_movies, recommended_movies_posters = [], []
    for movie_id in watched_movie_ids:
        if movie_id in movies['movie_id'].values:
            movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
            names, posters = recommend(movie_title)
            recommended_movies.extend(names)
            recommended_movies_posters.extend(posters)

    return recommended_movies[:5], recommended_movies_posters[:5]

# Function to add user rating
def add_rating(user_id, movie_id, rating):
    c.execute("INSERT INTO ratings (user_id, movie_id, rating) VALUES (?, ?, ?)", (user_id, movie_id, rating))
    conn.commit()

# Hybrid recommendations function
def hybrid_recommend(movie_title, user_id):
    # Get content-based recommendations
    recommended_movies, recommended_movies_posters = recommend(movie_title)
    
    # Get user-based collaborative recommendations
    watched_movies = []
    for row in c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,)):
        watched_movies.append(row[0])

    if watched_movies:
        additional_recommendations = []
        for movie_id in watched_movies:
            names, posters = recommend_based_on_history(user_id)
            additional_recommendations.extend(names)

        # Avoid duplicates and return final recommendations
        combined_recommendations = list(set(recommended_movies + additional_recommendations))
        combined_posters = list(set(recommended_movies_posters + [fetch_poster(movies[movies['title'] == m]['movie_id'].values[0]) for m in additional_recommendations]))
        return combined_recommendations[:5], combined_posters[:5]

    return recommended_movies, recommended_movies_posters

# Load movies and similarity matrices
movies_dict = pickle.load(open('movie_dict_4.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open('similarity_4.pkl', 'rb'))

# Streamlit UI components
st.title('🎬 Welcome to Bala Cinema! 🍿')
st.markdown('<p style="font-size:20px; font-style: italic;">Discover your next movie adventure with <strong>Bala Cinema</strong></p>', unsafe_allow_html=True)
st.write("A movie recommendation system by Bala Cinema")

# At the top of your script
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Login/Registration
auth_choice = st.selectbox("Login / Register", ["Login", "Register"])
username = st.text_input("Username")
password = st.text_input("Password", type='password')

if auth_choice == "Register":
    if st.button("Register", key="register_button"):
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            st.success("User registered successfully!")
        except sqlite3.IntegrityError:
            st.error("Username already exists!")
elif auth_choice == "Login":
    if st.button("Login", key="login_button"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user[2]):
                st.success("Login successful!")
                st.session_state.user_id = user[0]  # Store user ID in session state
            else:
                st.error("Invalid password!")
        else:
            st.error("User not found!")

# Check if user is logged in
if st.session_state.user_id:
    user_id = st.session_state.user_id
    # Show personalized recommendations
    st.write("Based on your watch history, you might like these:")
    names, posters = recommend_based_on_history(user_id)
    if names:
        for idx, (name, poster) in enumerate(zip(names, posters), start=1
        ):
            st.markdown(f"**MOVIE {idx}:** {name}")
            st.image(poster, width=200)
    else:
        st.write("You have no watch history yet. Start by searching for a movie to get recommendations!")
#    # Display current watch history
#     st.write("Your current watch history:")
#     watch_history = c.execute('SELECT movie_id FROM watch_history WHERE user_id=?', (user_id,)).fetchall()

#     if watch_history:
#         for wh in watch_history:
#             movie_id = wh[0]  # Directly use the movie ID
#             if movie_id in movies['movie_id'].values:  # Check if movie_id exists in movies DataFrame
#                 movie_title = movies[movies['movie_id'] == movie_id]['title'].values[0]
#                 st.markdown(f"- {movie_title}")
#             else:
#                 st.warning(f"Movie ID {movie_id} not found in movie database.")
#     else:
#         st.write("No movies in your watch history.")

    # # For debugging purposes
    # st.write("Current Movies DataFrame:")
    # st.dataframe(movies)

    # st.write("Watch History for User:")
    # st.write(watch_history)
# Select a movie for recommendations
selected_movie_name = st.selectbox(
    'Choose a reference movie to get started:',
    movies['title'].values
)

def simulate_loading():
    with st.spinner('Fetching recommendations...'):
        time.sleep(1.5)  # Simulate loading time
    st.success('Recommendations fetched successfully!')

# Add movie to user history
if st.button("Add to Watch History"):
        movie_id = movies[movies['title'] == selected_movie_name].iloc[0].movie_id
        try:
            # Insert into watch history as integer
            c.execute("INSERT INTO watch_history (user_id, movie_id) VALUES (?, ?)", (user_id, int(movie_id)))
            conn.commit()
            st.success(f"{selected_movie_name} added to your watch history!")
        except sqlite3.IntegrityError:
            st.error(f"Movie '{selected_movie_name}' already exists in your watch history!")
# Inside the 'Show me recommendations!' button click handler
if st.button('Show me recommendations!'):
    simulate_loading()
    names, posters = hybrid_recommend(selected_movie_name, user_id)
    st.write('Here are some movies you might enjoy:')
    st.markdown(f'### Recommended Movies based on *{selected_movie_name}*:')

    for idx, (name, poster) in enumerate(zip(names, posters), start=1):
        movie_info = movies[movies['title'] == name].iloc[0]

        # Add a rating option
        rating = st.slider(f'Rate {name}:', 1, 5)
        if st.button(f'Submit Rating for {name}'):
            add_rating(user_id, movie_info['movie_id'], rating)
            st.success(f'Rating submitted for {name}!')

        # Display movie details
        st.markdown(f"**MOVIE {idx}:** {name}")
        st.image(poster, width=200)

        # Clean and simple output for movie attributes
        cast_str = ', '.join(movie_info['cast'])  # Join cast members with a comma
        rating_str = ''.join(movie_info['vote_average'])  # Convert rating to string
        genre_str = ', '.join(movie_info['genres'])  # Join genres with a comma
        runtime_str = ''.join(movie_info['runtime']) + ' minutes'  # Format runtime
        release_date_str = ''.join(movie_info['release_date']) # Use release date as is
        about_str = ' '.join(movie_info['overview'])  # Join overview words into a sentence

        st.markdown(f"**CAST:** {cast_str}")
        st.markdown(f"**MOVIE RATING:** {rating_str}")
        st.markdown(f"**GENRE:** {genre_str}")
        st.markdown(f"**RUNTIME:** {runtime_str}")
        st.markdown(f"**RELEASE DATE:** {release_date_str}")
        st.markdown(f"**ABOUT:** {about_str}")