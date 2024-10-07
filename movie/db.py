import sqlite3

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file. """
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        print(f"Connection to {db_file} established.")
    except sqlite3.Error as e:
        print(f"Error {e} occurred while connecting to the database.")
    
    return conn

def setup_database(conn):
    """ Create tables in the database if they do not exist. """
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')

    # Create watch_history table
    c.execute('''CREATE TABLE IF NOT EXISTS watch_history (
                    user_id INTEGER,
                    movie_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    # Create ratings table
    c.execute('''CREATE TABLE IF NOT EXISTS ratings (
                    user_id INTEGER,
                    movie_id INTEGER,
                    rating REAL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(movie_id) REFERENCES watch_history(movie_id))''')
    
    conn.commit()
    print("Database setup complete.")

if __name__ == "__main__":
    # Main execution
    database_file = "movie_recommendation.db"  # Database file name
    connection = create_connection(database_file)  # Create a database connection
    setup_database(connection)  # Set up the database tables

    # Close the connection when done
    if connection:
        connection.close()
        print("Database connection closed.")
