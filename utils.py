from datetime import datetime, timedelta
from typing import List

# Updated categories to match your workout split + running workouts
CATEGORIES = [
    "Lower Strength",
    "Upper Strength", 
    "Lower Volume / Hypertrophy",
    "Upper Volume / Hypertrophy",
    "Easy Run",
    "Tempo Run",
    "Long Easy Run",
    "Other"
]

def format_date(date_str: str) -> str:
    """Format ISO date to readable format"""
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.strftime("%B %d, %Y")
    except:
        return date_str

def get_date_range(days_back: int = 30):
    """Get date range for queries"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    return start_date.isoformat(), end_date.isoformat()

def validate_set_input(reps: int, weight: float) -> tuple[bool, str]:
    """Validate set input"""
    if reps <= 0:
        return False, "Reps must be positive"
    if weight < 0:
        return False, "Weight cannot be negative"
    if reps > 100:
        return False, "Reps seems too high (>100)"
    if weight > 1000:
        return False, "Weight seems too high (>1000)"
    return True, ""