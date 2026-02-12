import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from contextlib import contextmanager
import pytz
import auth  # <-- ADDED FOR AUTHENTICATION

# Set timezone
EST = pytz.timezone('America/New_York')

def get_today():
    """Get today's date in EST"""
    return datetime.now(EST).date()

def get_now():
    """Get current datetime in EST"""
    return datetime.now(EST)

def get_connection_string():
    """Get PostgreSQL connection string from Streamlit secrets or environment"""
    try:
        # Try Streamlit secrets first (for deployment)
        conn_str = st.secrets["connections"]["postgresql"]["url"]
        return conn_str
    except Exception as e:
        # Show error instead of silent fallback
        st.error(f"❌ Cannot connect to database. Error: {str(e)}")
        st.error("Please check your Streamlit Secrets configuration.")
        st.stop()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
        # Set timezone to EST for this connection
        cursor = conn.cursor()
        cursor.execute("SET TIME ZONE 'America/New_York'")
        conn.commit()
        
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize database with schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create categories table (NEW)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, user_id)
            )
        """)
        
        # Create exercises table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, user_id)
            )
        """)
        
        # Create workouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id SERIAL PRIMARY KEY,
                workout_date DATE NOT NULL,
                notes TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create sets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                id SERIAL PRIMARY KEY,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                weight REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        
        # Create templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                day_of_week TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create template_exercises table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_exercises (
                id SERIAL PRIMARY KEY,
                template_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                exercise_order INTEGER DEFAULT 0,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        
        # Create PR tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_records (
                id SERIAL PRIMARY KEY,
                exercise_id INTEGER NOT NULL,
                pr_type TEXT NOT NULL,
                value REAL NOT NULL,
                achieved_date DATE NOT NULL,
                context TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_workout ON sets(workout_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_exercise ON sets(exercise_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(workout_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_exercises ON template_exercises(template_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_exercise ON personal_records(exercise_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_date ON personal_records(achieved_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_created ON sets(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date_desc ON workouts(workout_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_workout_exercise ON sets(workout_id, exercise_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_user ON exercises(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user ON workouts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_user ON personal_records(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
        conn.commit()
    
    migrate_exercises_for_multiuser()

# ==================== CATEGORIES ====================

def add_category(name: str, user_id: int = None) -> int:
    """Add a new category for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, user_id) VALUES (%s, %s) RETURNING id",
            (name.strip(), user_id)
        )
        category_id = cursor.fetchone()['id']
    
    # Clear the cache so new category shows up immediately
    get_all_categories_cached.clear()
    
    return category_id
def get_all_categories(user_id: int = None) -> List[Dict]:
    """Get all categories for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE user_id = %s ORDER BY name",
            (user_id,)
        )
        result = cursor.fetchall()
        return [dict(row) for row in result] if result else []  # ✅ Explicit empty list

def delete_category(category_id: int, user_id: int = None):
    """Delete a category (with user verification)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM categories WHERE id = %s AND user_id = %s",
            (category_id, user_id)
        )
    
    # Clear the cache so deletion shows up immediately
    get_all_categories_cached.clear()

def get_category_by_name(name: str, user_id: int = None) -> Optional[Dict]:
    """Get category by name for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE name = %s AND user_id = %s",
            (name, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

@st.cache_data(ttl=300)
def get_all_categories_cached(user_id: int = None):
    if user_id is None:
        user_id = auth.get_current_user_id()
    result = get_all_categories(user_id)
    return result if result is not None else []  # ✅ Extra safety

# ==================== EXERCISES ====================

def add_exercise(name: str, category: str = None, user_id: int = None) -> int:
    """Add a new exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if exercise already exists for this user
        cursor.execute(
            "SELECT id FROM exercises WHERE name = %s AND user_id = %s",
            (name.strip(), user_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Return existing exercise ID instead of trying to create duplicate
            return existing['id']
        
        # Create new exercise
        cursor.execute(
            "INSERT INTO exercises (name, category, user_id) VALUES (%s, %s, %s) RETURNING id",
            (name.strip(), category, user_id)
        )
        exercise_id = cursor.fetchone()['id']
    
    # Clear the cache
    get_all_exercises_cached.clear()
    
    return exercise_id


def get_all_exercises(user_id: int = None) -> List[Dict]:
    """Get all exercises for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM exercises WHERE user_id = %s ORDER BY name",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_exercise_by_name(name: str, user_id: int = None) -> Optional[Dict]:
    """Get exercise by name for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM exercises WHERE name = %s AND user_id = %s",
            (name, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_exercise(exercise_id: int, user_id: int = None):
    """Delete an exercise (with user verification)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM exercises WHERE id = %s AND user_id = %s",
            (exercise_id, user_id)
        )
    
    # Clear the cache
    get_all_exercises_cached.clear()

def update_set(set_id: int, reps: int, weight: float):
    """Update a specific set's reps and weight"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sets SET reps = %s, weight = %s WHERE id = %s",
            (reps, weight, set_id)
        )

# ==================== WORKOUTS ====================

def create_workout(workout_date: str, notes: str = None, user_id: int = None) -> int:
    """Create a new workout session for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workouts (workout_date, notes, user_id) VALUES (%s, %s, %s) RETURNING id",
            (workout_date, notes, user_id)
        )
        return cursor.fetchone()['id']

def get_or_create_todays_workout(user_id: int = None) -> int:
    """Get today's workout or create if doesn't exist for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    today = get_today().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM workouts WHERE workout_date = %s AND user_id = %s",
            (today, user_id)
        )
        row = cursor.fetchone()
        
        if row:
            return row['id']
        else:
            return create_workout(today, user_id=user_id)

def get_workouts_by_date_range(start_date: str, end_date: str, user_id: int = None) -> List[Dict]:
    """Get workouts within date range for a specific user (only those with sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.* FROM workouts w
            WHERE w.workout_date BETWEEN %s AND %s
            AND w.user_id = %s
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
            ORDER BY w.workout_date DESC
        """, (start_date, end_date, user_id))
        return [dict(row) for row in cursor.fetchall()]

def get_workout_details(workout_id: int) -> Dict:
    """Get full workout details with sets"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get workout info
        cursor.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
        workout = dict(cursor.fetchone())
        
        # Get all sets with exercise names
        cursor.execute("""
            SELECT s.*, e.name as exercise_name, e.category
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = %s
            ORDER BY s.created_at
        """, (workout_id,))
        
        workout['sets'] = [dict(row) for row in cursor.fetchall()]
        return workout

def delete_workout(workout_id: int):
    """Delete a workout (cascade deletes sets)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workouts WHERE id = %s", (workout_id,))

def get_workout_by_id(workout_id: int) -> Optional[Dict]:
    """Get workout by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_workout_notes(workout_id: int, notes: str):
    """Update notes for a workout"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workouts SET notes = %s WHERE id = %s",
            (notes, workout_id)
        )

# ==================== SETS ====================

def add_set(workout_id: int, exercise_id: int, reps: int, weight: float) -> int:
    """Add a set to a workout"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get next set number for this exercise in this workout
        cursor.execute("""
            SELECT COALESCE(MAX(set_number), 0) + 1 as next_set
            FROM sets
            WHERE workout_id = %s AND exercise_id = %s
        """, (workout_id, exercise_id))
        set_number = cursor.fetchone()['next_set']
        
        cursor.execute("""
            INSERT INTO sets (workout_id, exercise_id, set_number, reps, weight)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (workout_id, exercise_id, set_number, reps, weight))
        
        return cursor.fetchone()['id']

def get_sets_for_workout(workout_id: int) -> pd.DataFrame:
    """Get all sets for a workout as DataFrame"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, e.name as exercise, s.set_number, s.reps, s.weight,
                   s.created_at
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = %s
            ORDER BY s.created_at
        """, (workout_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        # Convert RealDictCursor results to DataFrame
        return pd.DataFrame([dict(row) for row in rows])

def delete_set(set_id: int):
    """Delete a specific set"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sets WHERE id = %s", (set_id,))

# ==================== PROGRESS ====================

def get_exercise_progress(exercise_id: int, limit: int = 100, user_id: int = None) -> pd.DataFrame:
    """Get historical data for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT w.workout_date, s.set_number, s.reps, s.weight,
                   (s.reps * s.weight) as volume
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            ORDER BY w.workout_date DESC, s.set_number
            LIMIT %s
        """
        return pd.read_sql_query(query, conn, params=(exercise_id, user_id, limit))

def get_exercise_stats(exercise_id: int, user_id: int = None) -> Dict:
    """Get summary stats for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT s.workout_id) as total_workouts,
                COUNT(*) as total_sets,
                MAX(s.weight) as max_weight,
                AVG(s.reps) as avg_reps,
                MAX(s.reps * s.weight) as max_volume
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
        """, (exercise_id, user_id))
        
        row = cursor.fetchone()
        return dict(row) if row else {}

# ==================== WORKOUT TEMPLATES ====================

def create_template(name: str, day_of_week: str = None, user_id: int = None) -> int:
    """Create a workout template for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO templates (name, day_of_week, user_id) VALUES (%s, %s, %s) RETURNING id",
            (name, day_of_week, user_id)
        )
        return cursor.fetchone()['id']

def add_exercise_to_template(template_id: int, exercise_id: int, order: int = 0):
    """Add an exercise to a template"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO template_exercises (template_id, exercise_id, exercise_order) VALUES (%s, %s, %s)",
            (template_id, exercise_id, order)
        )

def get_all_templates(user_id: int = None) -> List[Dict]:
    """Get all templates for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM templates WHERE user_id = %s ORDER BY name",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_template_exercises(template_id: int) -> List[Dict]:
    """Get exercises for a template"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*, te.exercise_order
            FROM template_exercises te
            JOIN exercises e ON te.exercise_id = e.id
            WHERE te.template_id = %s
            ORDER BY te.exercise_order
        """, (template_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_template(template_id: int, user_id: int = None):
    """Delete a template (with user verification)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM templates WHERE id = %s AND user_id = %s",
            (template_id, user_id)
        )

# ==================== PREVIOUS SESSION DATA ====================

def get_last_workout_for_exercise(exercise_id: int, before_date: str = None, user_id: int = None) -> Optional[Dict]:
    """Get the most recent workout data for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if before_date:
            cursor.execute("""
                SELECT w.workout_date, s.set_number, s.reps, s.weight
                FROM sets s
                JOIN workouts w ON s.workout_id = w.id
                JOIN exercises e ON s.exercise_id = e.id
                WHERE s.exercise_id = %s AND w.workout_date < %s AND e.user_id = %s
                ORDER BY w.workout_date DESC, s.set_number
                LIMIT 10
            """, (exercise_id, before_date, user_id))
        else:
            cursor.execute("""
                SELECT w.workout_date, s.set_number, s.reps, s.weight
                FROM sets s
                JOIN workouts w ON s.workout_id = w.id
                JOIN exercises e ON s.exercise_id = e.id
                WHERE s.exercise_id = %s AND e.user_id = %s
                ORDER BY w.workout_date DESC, s.set_number
                LIMIT 10
            """, (exercise_id, user_id))
        
        rows = cursor.fetchall()
        if not rows:
            return None
        
        return {
            'date': rows[0]['workout_date'],
            'sets': [dict(row) for row in rows]
        }

def get_exercise_pr(exercise_id: int, user_id: int = None) -> Dict:
    """Get personal records for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Max weight
        cursor.execute("""
            SELECT MAX(s.weight) as max_weight, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            GROUP BY s.exercise_id, w.workout_date
            ORDER BY max_weight DESC
            LIMIT 1
        """, (exercise_id, user_id))
        max_weight_row = cursor.fetchone()
        
        # Max volume in single workout
        cursor.execute("""
            SELECT SUM(s.reps * s.weight) as max_volume, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            GROUP BY s.workout_id, w.workout_date
            ORDER BY max_volume DESC
            LIMIT 1
        """, (exercise_id, user_id))
        max_volume_row = cursor.fetchone()
        
        # Max reps at any weight
        cursor.execute("""
            SELECT MAX(s.reps) as max_reps, s.weight, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            GROUP BY s.weight, w.workout_date
            ORDER BY max_reps DESC
            LIMIT 1
        """, (exercise_id, user_id))
        max_reps_row = cursor.fetchone()
        
        return {
            'max_weight': dict(max_weight_row) if max_weight_row else None,
            'max_volume': dict(max_volume_row) if max_volume_row else None,
            'max_reps': dict(max_reps_row) if max_reps_row else None
        }

def check_if_pr(exercise_id: int, weight: float, reps: int, workout_date: str, user_id: int = None) -> Dict:
    """Check if current set is a PR for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check max weight PR
        cursor.execute("""
            SELECT MAX(s.weight) as prev_max
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND w.workout_date < %s AND e.user_id = %s
        """, (exercise_id, workout_date, user_id))
        
        result = cursor.fetchone()
        prev_max = result['prev_max'] if result and result['prev_max'] else 0
        
        is_weight_pr = weight > prev_max
        
        # Check estimated 1RM PR
        current_1rm = weight * (1 + reps / 30.0) if reps > 1 else weight
        
        cursor.execute("""
            SELECT MAX(s.weight * (1 + s.reps / 30.0)) as prev_1rm
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND w.workout_date < %s AND e.user_id = %s
        """, (exercise_id, workout_date, user_id))
        
        result = cursor.fetchone()
        prev_1rm = result['prev_1rm'] if result and result['prev_1rm'] else 0
        
        is_1rm_pr = current_1rm > prev_1rm
        
        return {
            'is_weight_pr': is_weight_pr,
            'previous_max': prev_max,
            'is_1rm_pr': is_1rm_pr,
            'previous_1rm': prev_1rm
        }

# ==================== RUNNING-SPECIFIC FUNCTIONS ====================

def update_last_set_hr(workout_id: int, exercise_id: int, heart_rate: int):
    """Update the most recent set's set_number field with heart rate"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sets 
            SET set_number = %s
            WHERE id = (
                SELECT id FROM sets 
                WHERE workout_id = %s AND exercise_id = %s
                ORDER BY created_at DESC 
                LIMIT 1
            )
        """, (heart_rate, workout_id, exercise_id))

def get_running_stats(exercise_id: int, user_id: int = None) -> pd.DataFrame:
    """Get running-specific stats for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT 
                w.workout_date,
                s.reps / 10.0 as miles,
                s.weight as time_minutes,
                s.weight / (s.reps / 10.0) as pace_min_per_mile,
                s.set_number as heart_rate
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            ORDER BY w.workout_date DESC
            LIMIT 100
        """
        return pd.read_sql_query(query, conn, params=(exercise_id, user_id))

def check_running_pr(exercise_id: int, miles: float, time_minutes: float, workout_date: str, user_id: int = None) -> Dict:
    """Check if current run is a PR for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        current_pace = time_minutes / miles
        
        # Check fastest pace PR
        cursor.execute("""
            SELECT MIN(s.weight / (s.reps / 10.0)) as best_pace
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND w.workout_date < %s AND e.user_id = %s
        """, (exercise_id, workout_date, user_id))
        
        result = cursor.fetchone()
        prev_best_pace = result['best_pace'] if result and result['best_pace'] else 999
        
        is_pace_pr = current_pace < prev_best_pace
        
        # Check longest distance PR
        cursor.execute("""
            SELECT MAX(s.reps / 10.0) as max_distance
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND w.workout_date < %s AND e.user_id = %s
        """, (exercise_id, workout_date, user_id))
        
        result = cursor.fetchone()
        prev_max_distance = result['max_distance'] if result and result['max_distance'] else 0
        
        is_distance_pr = miles > prev_max_distance
        
        return {
            'is_pace_pr': is_pace_pr,
            'previous_best_pace': prev_best_pace if prev_best_pace != 999 else 0,
            'is_distance_pr': is_distance_pr,
            'previous_max_distance': prev_max_distance
        }

def get_running_prs(exercise_id: int, user_id: int = None) -> Dict:
    """Get running PRs for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Fastest pace
        cursor.execute("""
            SELECT 
                MIN(s.weight / (s.reps / 10.0)) as pace,
                w.workout_date as date,
                s.reps / 10.0 as miles
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            GROUP BY w.workout_date, s.reps
            ORDER BY pace ASC
            LIMIT 1
        """, (exercise_id, user_id))
        fastest_pace = cursor.fetchone()
        
        # Longest distance
        cursor.execute("""
            SELECT 
                MAX(s.reps / 10.0) as miles,
                w.workout_date as date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.exercise_id = %s AND e.user_id = %s
            GROUP BY w.workout_date
            ORDER BY miles DESC
            LIMIT 1
        """, (exercise_id, user_id))
        longest_distance = cursor.fetchone()
        
        return {
            'fastest_pace': dict(fastest_pace) if fastest_pace and fastest_pace['pace'] else None,
            'longest_distance': dict(longest_distance) if longest_distance and longest_distance['miles'] else None
        }

# ==================== PR TRACKING ====================

def log_pr(exercise_id: int, pr_type: str, value: float, achieved_date: str, context: str = None, user_id: int = None):
    """Log a new personal record for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO personal_records (exercise_id, pr_type, value, achieved_date, context, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (exercise_id, pr_type, value, achieved_date, context, user_id))

def get_recent_prs(days: int = 30, user_id: int = None) -> List[Dict]:
    """Get PRs from the last N days for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    cutoff_date = (get_now() - timedelta(days=days)).date().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pr.*, e.name as exercise_name
            FROM personal_records pr
            JOIN exercises e ON pr.exercise_id = e.id
            WHERE pr.achieved_date >= %s AND pr.user_id = %s
            ORDER BY pr.achieved_date DESC
        """, (cutoff_date, user_id))
        
        return [dict(row) for row in cursor.fetchall()]

def get_pr_history(exercise_id: int, user_id: int = None) -> pd.DataFrame:
    """Get PR history for an exercise for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT pr_type, value, achieved_date, context
            FROM personal_records
            WHERE exercise_id = %s AND user_id = %s
            ORDER BY achieved_date ASC
        """
        return pd.read_sql_query(query, conn, params=(exercise_id, user_id))

# ==================== WEEKLY MILEAGE TRACKING ====================

def get_weekly_mileage(user_id: int = None) -> pd.DataFrame:
    """Get weekly running mileage totals for a specific user (only workouts with sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT 
                EXTRACT(WEEK FROM w.workout_date)::INTEGER as week,
                EXTRACT(YEAR FROM w.workout_date)::INTEGER as year,
                SUM(s.reps / 10.0) as total_miles,
                COUNT(DISTINCT w.id) as num_runs
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE e.category IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            AND e.user_id = %s
            GROUP BY EXTRACT(YEAR FROM w.workout_date), EXTRACT(WEEK FROM w.workout_date)
            ORDER BY year, week
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df

def get_monthly_mileage(user_id: int = None) -> pd.DataFrame:
    """Get monthly running mileage totals for a specific user (only workouts with sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT 
                EXTRACT(MONTH FROM w.workout_date)::INTEGER as month,
                EXTRACT(YEAR FROM w.workout_date)::INTEGER as year,
                SUM(s.reps / 10.0) as total_miles,
                COUNT(DISTINCT w.id) as num_runs
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE e.category IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            AND e.user_id = %s
            GROUP BY EXTRACT(YEAR FROM w.workout_date), EXTRACT(MONTH FROM w.workout_date)
            ORDER BY year, month
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df

# ==================== DASHBOARD FUNCTIONS ====================

def get_week_summary(start_date: str, end_date: str, user_id: int = None) -> Dict:
    """Get summary stats for a week for a specific user (only counts workouts with sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get strength training volume
        cursor.execute("""
            SELECT COALESCE(SUM(s.reps * s.weight), 0) as total_volume
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE w.workout_date BETWEEN %s AND %s
            AND e.category NOT IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            AND e.user_id = %s
        """, (start_date, end_date, user_id))
        volume_result = cursor.fetchone()
        total_volume = volume_result['total_volume'] if volume_result else 0
        
        # Get running mileage
        cursor.execute("""
            SELECT COALESCE(SUM(s.reps / 10.0), 0) as total_miles
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE w.workout_date BETWEEN %s AND %s
            AND e.category IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            AND e.user_id = %s
        """, (start_date, end_date, user_id))
        miles_result = cursor.fetchone()
        total_miles = miles_result['total_miles'] if miles_result else 0
        
        # Get number of workouts (only those with sets)
        cursor.execute("""
            SELECT COUNT(DISTINCT w.id) as num_workouts
            FROM workouts w
            WHERE w.workout_date BETWEEN %s AND %s
            AND w.user_id = %s
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
        """, (start_date, end_date, user_id))
        workout_result = cursor.fetchone()
        num_workouts = workout_result['num_workouts'] if workout_result else 0
        
        return {
            'total_volume': total_volume,
            'total_miles': total_miles,
            'num_workouts': num_workouts
        }

def get_workout_streak(user_id: int = None) -> int:
    """Calculate current workout streak for a specific user (consecutive days with workouts that have sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all workout dates that have sets, ordered descending
        cursor.execute("""
            SELECT DISTINCT w.workout_date
            FROM workouts w
            WHERE w.user_id = %s
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
            ORDER BY w.workout_date DESC
        """, (user_id,))
        
        dates = [row['workout_date'] for row in cursor.fetchall()]
        
        if not dates:
            return 0
        
        # Check if today or yesterday has a workout
        today = get_today()
        yesterday = today - timedelta(days=1)
        
        most_recent = dates[0]
        
        if most_recent != today and most_recent != yesterday:
            return 0
        
        # Count consecutive days
        streak = 1
        expected_date = most_recent - timedelta(days=1)
        
        for date in dates[1:]:
            if date == expected_date:
                streak += 1
                expected_date = date - timedelta(days=1)
            else:
                break
        
        return streak

def get_days_since_last_workout(user_id: int = None) -> int:
    """Get number of days since last workout for a specific user (with sets)"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(w.workout_date) as last_date
            FROM workouts w
            WHERE w.user_id = %s
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result or not result['last_date']:
            return 999  # No workouts ever
        
        last_date = result['last_date']
        today = get_today()
        
        return (today - last_date).days

def get_category_volume_this_week(start_date: str, end_date: str, user_id: int = None) -> pd.DataFrame:
    """Get volume by category for this week for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            SELECT 
                e.category,
                SUM(s.reps * s.weight) as volume
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE w.workout_date BETWEEN %s AND %s
            AND e.category NOT IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            AND e.user_id = %s
            GROUP BY e.category
            ORDER BY volume DESC
        """
        return pd.read_sql_query(query, conn, params=(start_date, end_date, user_id))

def get_weekly_volume_trend(weeks: int = 8, user_id: int = None) -> pd.DataFrame:
    """Get weekly volume trend for a specific user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        query = """
            WITH weekly_data AS (
                SELECT 
                    EXTRACT(WEEK FROM w.workout_date)::INTEGER as week,
                    EXTRACT(YEAR FROM w.workout_date)::INTEGER as year,
                    SUM(s.reps * s.weight) as volume,
                    w.workout_date
                FROM sets s
                JOIN workouts w ON s.workout_id = w.id
                JOIN exercises e ON s.exercise_id = e.id
                WHERE e.category NOT IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
                AND e.user_id = %s
                GROUP BY 
                    EXTRACT(YEAR FROM w.workout_date), 
                    EXTRACT(WEEK FROM w.workout_date),
                    w.workout_date
            )
            SELECT 
                week,
                year,
                SUM(volume) as volume
            FROM weekly_data
            GROUP BY year, week
            ORDER BY year ASC, week ASC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
        # Return only the last N weeks
        if not df.empty and len(df) > weeks:
            df = df.tail(weeks)
        
        return df
    
def get_workout_by_date(workout_date: str, user_id: int = None) -> Optional[Dict]:
    """Get workout for a specific date and user"""
    if user_id is None:
        user_id = auth.get_current_user_id()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM workouts WHERE workout_date = %s AND user_id = %s",
            (workout_date, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
@st.cache_data(ttl=300)
def get_all_exercises_cached(user_id: int = None):
    if user_id is None:
        user_id = auth.get_current_user_id()
    return get_all_exercises(user_id)

def migrate_exercises_for_multiuser():
    """One-time migration to fix exercises without user_id"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if there are any exercises without user_id
        cursor.execute("SELECT COUNT(*) as count FROM exercises WHERE user_id IS NULL")
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            print(f"Found {result['count']} exercises without user_id. Migrating...")
            
            # Get current user if authenticated
            try:
                current_user_id = auth.get_current_user_id()
                
                # Assign all orphaned exercises to current user
                cursor.execute(
                    "UPDATE exercises SET user_id = %s WHERE user_id IS NULL",
                    (current_user_id,)
                )
                conn.commit()
                print(f"Migration complete! Assigned {result['count']} exercises to user {current_user_id}")
            except:
                # If no user is authenticated, delete orphaned exercises
                cursor.execute("DELETE FROM exercises WHERE user_id IS NULL")
                conn.commit()
                print(f"Deleted {result['count']} orphaned exercises")
        else:
            print("No migration needed - all exercises have user_id")



def migrate_unique_constraints():
    """Fix unique constraints for multi-user support"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check existing constraints on exercises table
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'exercises' 
            AND constraint_type = 'UNIQUE'
        """)
        constraints = [row['constraint_name'] for row in cursor.fetchall()]
        
        # Drop old single-column constraint if it exists
        if 'exercises_name_key' in constraints:
            cursor.execute("ALTER TABLE exercises DROP CONSTRAINT exercises_name_key")
        
        # Add correct composite constraint if missing
        if 'exercises_name_user_id_key' not in constraints:
            cursor.execute("""
                ALTER TABLE exercises 
                ADD CONSTRAINT exercises_name_user_id_key 
                UNIQUE (name, user_id)
            """)
        
        # Check existing constraints on categories table
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'categories' 
            AND constraint_type = 'UNIQUE'
        """)
        constraints = [row['constraint_name'] for row in cursor.fetchall()]
        
        # Drop old single-column constraint if it exists
        if 'categories_name_key' in constraints:
            cursor.execute("ALTER TABLE categories DROP CONSTRAINT categories_name_key")
        
        # Add correct composite constraint if missing
        if 'categories_name_user_id_key' not in constraints:
            cursor.execute("""
                ALTER TABLE categories 
                ADD CONSTRAINT categories_name_user_id_key 
                UNIQUE (name, user_id)
            """)
        
        conn.commit()





