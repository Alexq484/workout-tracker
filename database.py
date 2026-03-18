import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from contextlib import contextmanager
import pytz

# Set timezone
EST = pytz.timezone('America/New_York')

def get_today():
    """Get today's date in EST"""
    return datetime.now(EST).date()

def get_now():
    """Get current datetime in EST"""
    return datetime.now(EST)

def get_connection_string():
    """Get PostgreSQL connection string from Streamlit secrets"""
    try:
        return st.secrets["connections"]["postgresql"]["url"]
    except Exception as e:
        st.error(f"❌ Cannot connect to database. Error: {str(e)}")
        st.stop()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
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
        
        # Create categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create exercises table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create workouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id SERIAL PRIMARY KEY,
                workout_date DATE NOT NULL,
                notes TEXT,
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
        
        # Create PR tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_records (
                id SERIAL PRIMARY KEY,
                exercise_id INTEGER NOT NULL,
                pr_type TEXT NOT NULL,
                value REAL NOT NULL,
                achieved_date DATE NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_workout ON sets(workout_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_exercise ON sets(exercise_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(workout_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_exercise ON personal_records(exercise_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date_desc ON workouts(workout_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_workout_exercise ON sets(workout_id, exercise_id)")
        
        conn.commit()

# ==================== CATEGORIES ====================

def add_category(name: str) -> int:
    """Add a new category"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name) VALUES (%s) RETURNING id",
            (name.strip(),)
        )
        category_id = cursor.fetchone()['id']
    get_all_categories_cached.clear()
    return category_id

def get_all_categories() -> List[Dict]:
    """Get all categories"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        result = cursor.fetchall()
        return [dict(row) for row in result] if result else []

def delete_category(category_id: int):
    """Delete a category"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
    get_all_categories_cached.clear()

def get_category_by_name(name: str) -> Optional[Dict]:
    """Get category by name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = %s", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

@st.cache_data(ttl=60)
def get_all_categories_cached():
    """Cached version of get_all_categories"""
    result = get_all_categories()
    return result if result is not None else []

# ==================== EXERCISES ====================

def add_exercise(name: str, category: str = None) -> int:
    """Add a new exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if exercise already exists
        cursor.execute("SELECT id FROM exercises WHERE name = %s", (name.strip(),))
        existing = cursor.fetchone()
        
        if existing:
            return existing['id']
        
        cursor.execute(
            "INSERT INTO exercises (name, category) VALUES (%s, %s) RETURNING id",
            (name.strip(), category)
        )
        exercise_id = cursor.fetchone()['id']
    
    get_all_exercises_cached.clear()
    return exercise_id

def get_all_exercises() -> List[Dict]:
    """Get all exercises"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exercises ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

def get_exercise_by_name(name: str) -> Optional[Dict]:
    """Get exercise by name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exercises WHERE name = %s", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_exercise(exercise_id: int):
    """Delete an exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
    get_all_exercises_cached.clear()

@st.cache_data(ttl=60)
def get_all_exercises_cached():
    """Cached version of get_all_exercises"""
    return get_all_exercises()

# ==================== WORKOUTS ====================

def create_workout(workout_date: str, notes: str = None) -> int:
    """Create a new workout session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workouts (workout_date, notes) VALUES (%s, %s) RETURNING id",
            (workout_date, notes)
        )
        return cursor.fetchone()['id']

def get_or_create_todays_workout() -> int:
    """Get today's workout or create if doesn't exist"""
    today = get_today().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM workouts WHERE workout_date = %s", (today,))
        row = cursor.fetchone()
        
        if row:
            return row['id']
        else:
            return create_workout(today)

def get_workouts_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Get workouts within date range (only those with sets)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.* FROM workouts w
            WHERE w.workout_date BETWEEN %s AND %s
            AND EXISTS (SELECT 1 FROM sets s WHERE s.workout_id = w.id)
            ORDER BY w.workout_date DESC
        """, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

def get_workout_details(workout_id: int) -> Dict:
    """Get full workout details with sets"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
        workout = dict(cursor.fetchone())
        
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
    """Delete a workout"""
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

def get_workout_by_date(workout_date: str) -> Optional[Dict]:
    """Get workout for a specific date"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workouts WHERE workout_date = %s", (workout_date,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_workout_notes(workout_id: int, notes: str):
    """Update notes for a workout"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE workouts SET notes = %s WHERE id = %s", (notes, workout_id))

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
            SELECT s.id, e.name as exercise, s.set_number, s.reps, s.weight, s.created_at
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = %s
            ORDER BY s.created_at
        """, (workout_id,))
        
        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame()
        
        return pd.DataFrame([dict(row) for row in rows])

def delete_set(set_id: int):
    """Delete a specific set"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sets WHERE id = %s", (set_id,))

def update_set(set_id: int, reps: int, weight: float):
    """Update a specific set's reps and weight"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sets SET reps = %s, weight = %s WHERE id = %s", (reps, weight, set_id))

# ==================== PREVIOUS SESSION DATA ====================

def get_last_workout_for_exercise(exercise_id: int, before_date: str = None) -> Optional[Dict]:
    """Get the most recent workout data for an exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if before_date:
            cursor.execute("""
                SELECT w.workout_date, s.set_number, s.reps, s.weight
                FROM sets s
                JOIN workouts w ON s.workout_id = w.id
                WHERE s.exercise_id = %s AND w.workout_date < %s
                ORDER BY w.workout_date DESC, s.set_number
                LIMIT 10
            """, (exercise_id, before_date))
        else:
            cursor.execute("""
                SELECT w.workout_date, s.set_number, s.reps, s.weight
                FROM sets s
                JOIN workouts w ON s.workout_id = w.id
                WHERE s.exercise_id = %s
                ORDER BY w.workout_date DESC, s.set_number
                LIMIT 10
            """, (exercise_id,))
        
        rows = cursor.fetchall()
        if not rows:
            return None
        
        return {
            'date': rows[0]['workout_date'],
            'sets': [dict(row) for row in rows]
        }

def get_exercise_pr(exercise_id: int) -> Dict:
    """Get personal records for an exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Max weight
        cursor.execute("""
            SELECT MAX(s.weight) as max_weight, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            GROUP BY s.exercise_id, w.workout_date
            ORDER BY max_weight DESC
            LIMIT 1
        """, (exercise_id,))
        max_weight_row = cursor.fetchone()
        
        # Max volume in single workout
        cursor.execute("""
            SELECT SUM(s.reps * s.weight) as max_volume, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            GROUP BY s.workout_id, w.workout_date
            ORDER BY max_volume DESC
            LIMIT 1
        """, (exercise_id,))
        max_volume_row = cursor.fetchone()
        
        return {
            'max_weight': dict(max_weight_row) if max_weight_row else None,
            'max_volume': dict(max_volume_row) if max_volume_row else None
        }

def check_if_pr(exercise_id: int, weight: float, reps: int, workout_date: str) -> Dict:
    """Check if current set is a PR"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check max weight PR
        cursor.execute("""
            SELECT MAX(s.weight) as prev_max
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s AND w.workout_date < %s
        """, (exercise_id, workout_date))
        
        result = cursor.fetchone()
        prev_max = result['prev_max'] if result and result['prev_max'] else 0
        is_weight_pr = weight > prev_max
        
        # Check estimated 1RM PR
        current_1rm = weight * (1 + reps / 30.0) if reps > 1 else weight
        
        cursor.execute("""
            SELECT MAX(s.weight * (1 + s.reps / 30.0)) as prev_1rm
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s AND w.workout_date < %s
        """, (exercise_id, workout_date))
        
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

def check_running_pr(exercise_id: int, miles: float, time_minutes: float, workout_date: str) -> Dict:
    """Check if current run is a PR"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        current_pace = time_minutes / miles
        
        # Check fastest pace PR
        cursor.execute("""
            SELECT MIN(s.weight / (s.reps / 10.0)) as best_pace
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s AND w.workout_date < %s
        """, (exercise_id, workout_date))
        
        result = cursor.fetchone()
        prev_best_pace = result['best_pace'] if result and result['best_pace'] else 999
        is_pace_pr = current_pace < prev_best_pace
        
        # Check longest distance PR
        cursor.execute("""
            SELECT MAX(s.reps / 10.0) as max_distance
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s AND w.workout_date < %s
        """, (exercise_id, workout_date))
        
        result = cursor.fetchone()
        prev_max_distance = result['max_distance'] if result and result['max_distance'] else 0
        is_distance_pr = miles > prev_max_distance
        
        return {
            'is_pace_pr': is_pace_pr,
            'previous_best_pace': prev_best_pace if prev_best_pace != 999 else 0,
            'is_distance_pr': is_distance_pr,
            'previous_max_distance': prev_max_distance
        }

# ==================== PR TRACKING ====================

def log_pr(exercise_id: int, pr_type: str, value: float, achieved_date: str, context: str = None):
    """Log a new personal record"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO personal_records (exercise_id, pr_type, value, achieved_date, context)
            VALUES (%s, %s, %s, %s, %s)
        """, (exercise_id, pr_type, value, achieved_date, context))
