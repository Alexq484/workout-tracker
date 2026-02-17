"""
Authentication module for workout tracking app
Handles user registration, login, and session management
"""

import streamlit as st
import hashlib
import secrets
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from streamlit_cookies_controller import CookieController

COOKIE_NAME = "workout_session_token"
TOKEN_EXPIRY_DAYS = 30

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
        
        # Check if users table exists and if email column needs to be made nullable
        cursor.execute("""
            SELECT column_name, is_nullable
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='email'
        """)
        
        email_col = cursor.fetchone()
        if email_col and email_col['is_nullable'] == 'NO':
            try:
                cursor.execute("ALTER TABLE users ALTER COLUMN email DROP NOT NULL")
                cursor.execute("""
                    DO $$ 
                    BEGIN
                        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
                    EXCEPTION
                        WHEN undefined_object THEN NULL;
                    END $$;
                """)
                conn.commit()
            except Exception as alter_error:
                conn.rollback()
                pass
        
        # ── NEW: session tokens table ──────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_tokens_token ON session_tokens(token)")
        # ──────────────────────────────────────────────────────────────────

        # Add user_id column to existing tables if they don't have it
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

# ── NEW: Token helpers ─────────────────────────────────────────────────────────

def create_session_token(user_id: int) -> str:
    """Generate a secure token, store it in DB, and return it"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRY_DAYS)
    
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO session_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    
    return token

def validate_session_token(token: str) -> dict | None:
    """Return user data if token is valid and not expired, else None"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username
            FROM session_tokens st
            JOIN users u ON st.user_id = u.user_id
            WHERE st.token = %s AND st.expires_at > NOW()
        """, (token,))
        result = cursor.fetchone()
        return dict(result) if result else None
    finally:
        cursor.close()
        conn.close()

def delete_session_token(token: str):
    """Delete a token from the DB (used on logout)"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM session_tokens WHERE token = %s", (token,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# ──────────────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str) -> tuple[bool, str]:
    """
    Create a new user account
    Returns (success, message)
    """
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        hashed_password, salt = hash_password(password)
        
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
        
        return True, "Account created successfully!"
    
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
        
        if verify_password(password, password_hash, password_salt):
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user_id)
            )
            conn.commit()
            
            return True, {'user_id': user_id, 'username': username}
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
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None

def check_persistent_login(cookie_controller: CookieController) -> bool:
    """
    Check browser cookie for an existing session token and auto-login if valid.
    Call this after init_session_state() when the user is not yet authenticated.
    """
    if st.session_state.get('authenticated'):
        return True
    
    try:
        token = cookie_controller.get(COOKIE_NAME)
    except Exception:
        return False

    if not token:
        return False
    
    user_data = validate_session_token(token)
    if user_data:
        st.session_state.authenticated = True
        st.session_state.user_id = user_data['user_id']
        st.session_state.username = user_data['username']
        st.session_state.session_token = token
        return True
    
    # Token expired or invalid — clear the stale cookie
    try:
        cookie_controller.remove(COOKIE_NAME)
    except Exception:
        pass
    return False

def logout(cookie_controller: CookieController = None):
    """Logout the current user and clear the persistent cookie"""
    token = st.session_state.get('session_token')
    if token:
        delete_session_token(token)
    
    if cookie_controller:
        try:
            cookie_controller.remove(COOKIE_NAME)
        except Exception:
            pass
    
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.session_token = None
    # Clear workout session state
    if 'workout_id' in st.session_state:
        st.session_state.workout_id = None
    if 'workout_active' in st.session_state:
        st.session_state.workout_active = False
    if 'workout_date' in st.session_state:
        st.session_state.workout_date = None

def login_page(cookie_controller: CookieController):
    """Display login/signup page"""
    st.title("🏋️ Workout Tracker")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Stay logged in for 30 days", value=True)
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
                        
                        if remember_me:
                            token = create_session_token(user_data['user_id'])
                            cookie_controller.set(
                                COOKIE_NAME,
                                token,
                                max_age=TOKEN_EXPIRY_DAYS * 86400  # seconds
                            )
                            st.session_state.session_token = token
                        
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
    """Decorator-like function to require authentication (no cookie support)"""
    if not st.session_state.get('authenticated', False):
        login_page(CookieController())
        st.stop()

def get_current_user_id():
    """Get the current logged-in user's ID"""
    return st.session_state.get('user_id')
