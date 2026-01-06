import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from contextlib import contextmanager

def get_connection_string():
    """Get PostgreSQL connection string from Streamlit secrets or environment"""
    try:
        # Try Streamlit secrets first (for deployment)
        return st.secrets["connections"]["postgresql"]["url"]
    except:
        # Fallback to local connection string for development
        # You can set this when testing locally
        return "postgresql://localhost/workout_tracker"

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg2.connect(get_connection_string(), cursor_factory=RealDictCursor)
    try:
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
        
        # Create templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                day_of_week TEXT,
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
        
        conn.commit()

# ==================== EXERCISES ====================

def add_exercise(name: str, category: str = None) -> int:
    """Add a new exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO exercises (name, category) VALUES (%s, %s) RETURNING id",
            (name.strip(), category)
        )
        return cursor.fetchone()['id']

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
    today = datetime.now().date().isoformat()
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
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
            ORDER BY w.workout_date DESC
        """, (start_date, end_date))
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
        query = """
            SELECT s.id, e.name as exercise, s.set_number, s.reps, s.weight,
                   s.created_at
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = %s
            ORDER BY s.created_at
        """
        return pd.read_sql_query(query, conn, params=(workout_id,))

def delete_set(set_id: int):
    """Delete a specific set"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sets WHERE id = %s", (set_id,))

# ==================== PROGRESS ====================

def get_exercise_progress(exercise_id: int, limit: int = 100) -> pd.DataFrame:
    """Get historical data for an exercise"""
    with get_db() as conn:
        query = """
            SELECT w.workout_date, s.set_number, s.reps, s.weight,
                   (s.reps * s.weight) as volume
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            ORDER BY w.workout_date DESC, s.set_number
            LIMIT %s
        """
        return pd.read_sql_query(query, conn, params=(exercise_id, limit))

def get_exercise_stats(exercise_id: int) -> Dict:
    """Get summary stats for an exercise"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT workout_id) as total_workouts,
                COUNT(*) as total_sets,
                MAX(weight) as max_weight,
                AVG(reps) as avg_reps,
                MAX(reps * weight) as max_volume
            FROM sets
            WHERE exercise_id = %s
        """, (exercise_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}

# ==================== WORKOUT TEMPLATES ====================

def create_template(name: str, day_of_week: str = None) -> int:
    """Create a workout template"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO templates (name, day_of_week) VALUES (%s, %s) RETURNING id",
            (name, day_of_week)
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

def get_all_templates() -> List[Dict]:
    """Get all templates"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY name")
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

def delete_template(template_id: int):
    """Delete a template"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM templates WHERE id = %s", (template_id,))

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
            SELECT MAX(weight) as max_weight, w.workout_date
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
            SELECT SUM(reps * weight) as max_volume, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            GROUP BY s.workout_id, w.workout_date
            ORDER BY max_volume DESC
            LIMIT 1
        """, (exercise_id,))
        max_volume_row = cursor.fetchone()
        
        # Max reps at any weight
        cursor.execute("""
            SELECT MAX(reps) as max_reps, weight, w.workout_date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            GROUP BY weight, w.workout_date
            ORDER BY max_reps DESC
            LIMIT 1
        """, (exercise_id,))
        max_reps_row = cursor.fetchone()
        
        return {
            'max_weight': dict(max_weight_row) if max_weight_row else None,
            'max_volume': dict(max_volume_row) if max_volume_row else None,
            'max_reps': dict(max_reps_row) if max_reps_row else None
        }

def check_if_pr(exercise_id: int, weight: float, reps: int, workout_date: str) -> Dict:
    """Check if current set is a PR"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check max weight PR
        cursor.execute("""
            SELECT MAX(weight) as prev_max
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
            SELECT MAX(weight * (1 + reps / 30.0)) as prev_1rm
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

def get_running_stats(exercise_id: int) -> pd.DataFrame:
    """Get running-specific stats for an exercise"""
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
            WHERE s.exercise_id = %s
            ORDER BY w.workout_date DESC
            LIMIT 100
        """
        return pd.read_sql_query(query, conn, params=(exercise_id,))

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

def get_running_prs(exercise_id: int) -> Dict:
    """Get running PRs for an exercise"""
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
            WHERE s.exercise_id = %s
            GROUP BY w.workout_date, s.reps
            ORDER BY pace ASC
            LIMIT 1
        """, (exercise_id,))
        fastest_pace = cursor.fetchone()
        
        # Longest distance
        cursor.execute("""
            SELECT 
                MAX(s.reps / 10.0) as miles,
                w.workout_date as date
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            WHERE s.exercise_id = %s
            GROUP BY w.workout_date
            ORDER BY miles DESC
            LIMIT 1
        """, (exercise_id,))
        longest_distance = cursor.fetchone()
        
        return {
            'fastest_pace': dict(fastest_pace) if fastest_pace and fastest_pace['pace'] else None,
            'longest_distance': dict(longest_distance) if longest_distance and longest_distance['miles'] else None
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

def get_recent_prs(days: int = 30) -> List[Dict]:
    """Get PRs from the last N days"""
    cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pr.*, e.name as exercise_name
            FROM personal_records pr
            JOIN exercises e ON pr.exercise_id = e.id
            WHERE pr.achieved_date >= %s
            ORDER BY pr.achieved_date DESC
        """, (cutoff_date,))
        
        return [dict(row) for row in cursor.fetchall()]

def get_pr_history(exercise_id: int) -> pd.DataFrame:
    """Get PR history for an exercise"""
    with get_db() as conn:
        query = """
            SELECT pr_type, value, achieved_date, context
            FROM personal_records
            WHERE exercise_id = %s
            ORDER BY achieved_date ASC
        """
        return pd.read_sql_query(query, conn, params=(exercise_id,))

# ==================== WEEKLY MILEAGE TRACKING ====================

def get_weekly_mileage() -> pd.DataFrame:
    """Get weekly running mileage totals (only workouts with sets)"""
    with get_db() as conn:
        query = """
            SELECT 
                EXTRACT(WEEK FROM w.workout_date) as week,
                EXTRACT(YEAR FROM w.workout_date) as year,
                SUM(s.reps / 10.0) as total_miles,
                COUNT(DISTINCT w.id) as num_runs
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE e.category IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            GROUP BY EXTRACT(YEAR FROM w.workout_date), EXTRACT(WEEK FROM w.workout_date)
            ORDER BY year, week
        """
        df = pd.read_sql_query(query, conn)
        df['week'] = df['week'].astype(int)
        df['year'] = df['year'].astype(int)
        return df

def get_monthly_mileage() -> pd.DataFrame:
    """Get monthly running mileage totals (only workouts with sets)"""
    with get_db() as conn:
        query = """
            SELECT 
                EXTRACT(MONTH FROM w.workout_date) as month,
                EXTRACT(YEAR FROM w.workout_date) as year,
                SUM(s.reps / 10.0) as total_miles,
                COUNT(DISTINCT w.id) as num_runs
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE e.category IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            GROUP BY EXTRACT(YEAR FROM w.workout_date), EXTRACT(MONTH FROM w.workout_date)
            ORDER BY year, month
        """
        df = pd.read_sql_query(query, conn)
        df['month'] = df['month'].astype(int)
        df['year'] = df['year'].astype(int)
        return df

# ==================== DASHBOARD FUNCTIONS ====================

def get_week_summary(start_date: str, end_date: str) -> Dict:
    """Get summary stats for a week (only counts workouts with sets)"""
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
        """, (start_date, end_date))
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
        """, (start_date, end_date))
        miles_result = cursor.fetchone()
        total_miles = miles_result['total_miles'] if miles_result else 0
        
        # Get number of workouts (only those with sets)
        cursor.execute("""
            SELECT COUNT(DISTINCT w.id) as num_workouts
            FROM workouts w
            WHERE w.workout_date BETWEEN %s AND %s
            AND EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
        """, (start_date, end_date))
        workout_result = cursor.fetchone()
        num_workouts = workout_result['num_workouts'] if workout_result else 0
        
        return {
            'total_volume': total_volume,
            'total_miles': total_miles,
            'num_workouts': num_workouts
        }

def get_workout_streak() -> int:
    """Calculate current workout streak (consecutive days with workouts that have sets)"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all workout dates that have sets, ordered descending
        cursor.execute("""
            SELECT DISTINCT w.workout_date
            FROM workouts w
            WHERE EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
            ORDER BY w.workout_date DESC
        """)
        
        dates = [row['workout_date'] for row in cursor.fetchall()]
        
        if not dates:
            return 0
        
        # Check if today or yesterday has a workout
        today = datetime.now().date()
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

def get_days_since_last_workout() -> int:
    """Get number of days since last workout (with sets)"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(w.workout_date) as last_date
            FROM workouts w
            WHERE EXISTS (
                SELECT 1 FROM sets s WHERE s.workout_id = w.id
            )
        """)
        
        result = cursor.fetchone()
        
        if not result or not result['last_date']:
            return 999  # No workouts ever
        
        last_date = result['last_date']
        today = datetime.now().date()
        
        return (today - last_date).days

def get_category_volume_this_week(start_date: str, end_date: str) -> pd.DataFrame:
    """Get volume by category for this week"""
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
            GROUP BY e.category
            ORDER BY volume DESC
        """
        return pd.read_sql_query(query, conn, params=(start_date, end_date))

def get_weekly_volume_trend(weeks: int = 8) -> pd.DataFrame:
    """Get weekly volume trend"""
    with get_db() as conn:
        query = """
            SELECT 
                EXTRACT(WEEK FROM w.workout_date) as week,
                EXTRACT(YEAR FROM w.workout_date) as year,
                SUM(s.reps * s.weight) as volume
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE e.category NOT IN ('Easy Run', 'Tempo Run', 'Long Easy Run')
            GROUP BY EXTRACT(YEAR FROM w.workout_date), EXTRACT(WEEK FROM w.workout_date)
            ORDER BY year DESC, week DESC
            LIMIT %s
        """
        df = pd.read_sql_query(query, conn, params=(weeks,))
        df['week'] = df['week'].astype(int)
        df['year'] = df['year'].astype(int)
        return df.sort_values(['year', 'week'])
