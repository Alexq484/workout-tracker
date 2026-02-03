"""
Authentication module for workout tracking app
Handles user registration, login, and session management
"""

import streamlit as st
import hashlib
import secrets
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection_string():
    """Get PostgreSQL connection string from Streamlit secrets"""
    try:
        return st.secrets["connections"]["postgresql"]["url"]
    except Exception as e:
        st.error(f"❌ Cannot connect to database. Error: {str(e)}")
        st.stop()

def hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash a password with a salt using SHA-256
    Returns (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Combine password and salt, then hash
    password_salt = f"{password}{salt}".encode('utf-8')
    hashed = hashlib.sha256(password_salt).hexdigest()
    
    return hashed, salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against a hash"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed_password

def init_auth_tables():
    """Initialize authentication tables in database"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        
        # Create users table (email is now nullable)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Add user_id column to existing tables if they don't have it
        # Check if column exists first
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='exercises' AND column_name='user_id'
        """)
        
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE exercises ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
            cursor.execute("ALTER TABLE workouts ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
            cursor.execute("ALTER TABLE templates ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
            cursor.execute("ALTER TABLE personal_records ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
        
        # Create indexes for user_id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_user ON exercises(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user ON workouts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_user ON personal_records(user_id)")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error initializing auth tables: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def create_user(username: str, password: str) -> tuple[bool, str]:
    """
    Create a new user account
    Returns (success, message)
    """
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        
        # Validate inputs
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        # Check if username already exists
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        # Hash password
        hashed_password, salt = hash_password(password)
        
        # Insert new user (email will be NULL)
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, password_salt, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
            """,
            (username, hashed_password, salt, datetime.now())
        )
        
        user_id = cursor.fetchone()['user_id']
        conn.commit()
        
        return True, f"Account created successfully!"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error creating account: {str(e)}"
    
    finally:
        cursor.close()
        conn.close()

def authenticate_user(username: str, password: str) -> tuple[bool, dict]:
    """
    Authenticate a user
    Returns (success, user_data)
    """
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT user_id, username, password_hash, password_salt
            FROM users
            WHERE username = %s
            """,
            (username,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            return False, {}
        
        user_id, username, password_hash, password_salt = result.values()
        
        # Verify password
        if verify_password(password, password_hash, password_salt):
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user_id)
            )
            conn.commit()
            
            user_data = {
                'user_id': user_id,
                'username': username
            }
            
            return True, user_data
        else:
            return False, {}
    
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, {}
    
    finally:
        cursor.close()
        conn.close()

def init_session_state():
    """Initialize session state for authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None

def logout():
    """Logout the current user"""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    # Clear workout session state
    if 'workout_id' in st.session_state:
        st.session_state.workout_id = None
    if 'workout_active' in st.session_state:
        st.session_state.workout_active = False
    if 'workout_date' in st.session_state:
        st.session_state.workout_date = None

def login_page():
    """Display login/signup page"""
    st.title("🏋️ Workout Tracker")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    success, user_data = authenticate_user(username, password)
                    
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_data['user_id']
                        st.session_state.username = user_data['username']
                        st.success(f"Welcome back, {user_data['username']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
    
    with tab2:
        st.subheader("Create new account")
        
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submit = st.form_submit_button("Sign Up", use_container_width=True, type="primary")
            
            if submit:
                if not new_username or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = create_user(new_username, new_password)
                    
                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                    else:
                        st.error(message)

def require_auth():
    """Decorator-like function to require authentication"""
    if not st.session_state.get('authenticated', False):
        login_page()
        st.stop()

def get_current_user_id():
    """Get the current logged-in user's ID"""
    return st.session_state.get('user_id')
