import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

import database as db
import utils

# Set timezone to EST
EST = pytz.timezone('America/New_York')

def get_today():
    """Get today's date in EST"""
    return datetime.now(EST).date()

def get_now():
    """Get current datetime in EST"""
    return datetime.now(EST)

# Page config
st.set_page_config(
    page_title="Workout Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
db.init_database()

# Initialize session state
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

# Custom CSS for mobile optimization
st.markdown("""
    <style>
    /* Mobile-first responsive design */
    
    /* Larger touch targets for mobile */
    .stButton>button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.1rem;
        padding: 0.75rem 1rem;
        touch-action: manipulation;
    }
    
    /* Larger form inputs */
    .stNumberInput input,
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox select {
        font-size: 1.1rem !important;
        min-height: 3rem;
        padding: 0.75rem !important;
    }
    
    /* Better spacing on mobile */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Responsive padding */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Better expandable sections */
    .streamlit-expanderHeader {
        font-size: 1.1rem;
        padding: 1rem;
    }
    
    /* Mobile-specific styles */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            position: fixed;
            left: -100%;
            transition: left 0.3s ease;
            z-index: 999;
            width: 80vw !important;
            max-width: 80vw !important;
        }
        
        section[data-testid="stSidebar"][aria-expanded="true"] {
            left: 0;
        }
        
        section[data-testid="stSidebar"] > div:first-child {
            width: 80vw;
        }
        
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            max-width: 100%;
        }
        
        [data-testid="collapsedControl"] {
            position: fixed;
            top: 0.5rem;
            left: 0.5rem;
            z-index: 1000;
        }
        
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
            margin-bottom: 0.5rem;
        }
        
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.25rem !important;
        }
        
        .stForm {
            padding: 0.5rem;
        }
    }
    
    /* Desktop adjustments */
    @media (min-width: 769px) {
        .stButton>button {
            min-height: 2.5rem;
            font-size: 1rem;
        }
        
        [data-testid="stSidebar"] > div {
            width: 21rem;
        }
    }
    
    /* Custom styled components */
    .last-session {
        background-color: #e7f3ff;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196F3;
        margin: 0.75rem 0;
        font-size: 1rem;
    }
    
    .notes-box {
        background-color: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0.5rem;
        font-style: italic;
        font-size: 1rem;
    }
    
    /* Better form submit buttons */
    .stForm button[type="submit"] {
        background-color: #667eea;
        color: white;
        font-weight: bold;
        min-height: 3.5rem;
        font-size: 1.2rem;
        margin-top: 1rem;
    }
    
    /* Improve expander visibility */
    details {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin-bottom: 0.75rem;
    }
    
    summary {
        cursor: pointer;
        font-weight: 600;
        padding: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
page = st.sidebar.radio(
    "Navigate",
    ["📝 Log Workout", "📅 History", "⚙️ Manage Exercises"],
    label_visibility="collapsed"
)

# Clean up page names (remove emojis for internal use)
page = page.split(" ", 1)[1] if " " in page else page

# ==================== HELPER FUNCTIONS ====================

def get_exercises_by_category(category: str):
    """Get all exercises for a specific category"""
    all_exercises = db.get_all_exercises_cached()
    return [e for e in all_exercises if e['category'] == category]

def calculate_estimated_1rm(weight: float, reps: int) -> float:
    """Calculate estimated 1RM using Epley formula"""
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)

# ==================== LOG WORKOUT PAGE ====================

if page == "Log Workout":
    st.title("📝 Log Workout")
    
    # Get today's date
    today = get_today()
    st.caption(f"{today.strftime('%A, %b %d, %Y')}")
    
    # Initialize session state for last logged set
    if 'last_exercise' not in st.session_state:
        st.session_state.last_exercise = None
    if 'last_reps' not in st.session_state:
        st.session_state.last_reps = 10
    if 'last_weight' not in st.session_state:
        st.session_state.last_weight = 135.0
    
    # Auto-load today's workout (or create if doesn't exist)
    workout_id = db.get_or_create_todays_workout()
    
    # Get current workout details
    current_workout = db.get_workout_by_id(workout_id)
    
    # Workout notes section
    with st.expander("📝 Workout Notes"):
        current_notes = current_workout['notes'] if current_workout and current_workout['notes'] else ""
        
        notes = st.text_area(
            "Notes",
            value=current_notes,
            placeholder="Felt strong, shoulder tight, etc.",
            height=100,
            key="workout_notes",
            label_visibility="collapsed"
        )
        
        if st.button("💾 Save Notes", use_container_width=True):
            db.update_workout_notes(workout_id, notes)
            st.success("Notes saved!")
    
    # Quick Start
    st.subheader("🚀 Quick Start")
    
    user_categories = db.get_all_categories_cached()
    
    if user_categories:
        num_cols = 2
        category_names = [c['name'] for c in user_categories]
        
        for i in range(0, len(category_names), num_cols):
            cols = st.columns(num_cols)
            
            for idx, category_name in enumerate(category_names[i:i+num_cols]):
                with cols[idx]:
                    if st.button(category_name, key=f"cat_{category_name}", use_container_width=True):
                        st.session_state.selected_category = category_name
                        st.rerun()
    else:
        st.info("💡 No categories yet. Go to ⚙️ Manage Exercises to create your workout splits!")
    
    # Show selected category
    if st.session_state.selected_category:
        st.info(f"**Active:** {st.session_state.selected_category}")
        if st.button("❌ Show All", use_container_width=True):
            st.session_state.selected_category = None
            st.rerun()
        
        exercises = get_exercises_by_category(st.session_state.selected_category)
    else:
        exercises = db.get_all_exercises_cached()
    
    st.divider()
    
    # Exercise selector
    st.subheader("Add Set")
    
    if not exercises:
        st.warning("⚠️ No exercises found")
        st.info("Add exercises in ⚙️ Manage Exercises")
    else:
        exercise_names = [e['name'] for e in exercises]
        
        default_index = 0
        if st.session_state.last_exercise and st.session_state.last_exercise in exercise_names:
            default_index = exercise_names.index(st.session_state.last_exercise)
        
        selected_exercise = st.selectbox(
            "Exercise",
            exercise_names,
            index=default_index,
            key="exercise_select"
        )
        
        # Get exercise object
        exercise = db.get_exercise_by_name(selected_exercise)

        with st.form(key=f"quick_log_{selected_exercise}", clear_on_submit=False):
            
            today_sets = db.get_sets_for_workout(workout_id)
            
            if not today_sets.empty and 'exercise' in today_sets.columns:
                todays_sets_for_exercise = today_sets[today_sets['exercise'] == selected_exercise]
            else:
                todays_sets_for_exercise = pd.DataFrame()

            if exercise:
                last_session = db.get_last_workout_for_exercise(
                    exercise['id'],
                    before_date=today.isoformat()
                )
                
                if last_session:
                    st.markdown(f"""
                    <div class="last-session">
                        <strong>📊 Last: {last_session['date']}</strong><br>
                        {len(last_session['sets'])} sets • 
                        {last_session['sets'][0]['reps']}-{last_session['sets'][-1]['reps']} reps • 
                        {last_session['sets'][0]['weight']}-{max(s['weight'] for s in last_session['sets'])} lbs
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if not todays_sets_for_exercise.empty:
                        most_recent = todays_sets_for_exercise.iloc[-1]
                        default_weight = float(most_recent['weight'])
                        default_reps = int(most_recent['reps'])
                    else:
                        default_weight = max(s['weight'] for s in last_session['sets'])
                        default_reps = last_session['sets'][0]['reps']
                else:
                    if not todays_sets_for_exercise.empty:
                        most_recent = todays_sets_for_exercise.iloc[-1]
                        default_weight = float(most_recent['weight'])
                        default_reps = int(most_recent['reps'])
                    else:
                        default_weight = 135.0
                        default_reps = 10
            else:
                default_weight = 135.0
                default_reps = 10
            
            # Strength training inputs
            reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps, step=1)
            weight = st.number_input("Weight (lbs)", min_value=0.0, max_value=1000.0, value=default_weight, step=5.0)
            
            est_1rm = calculate_estimated_1rm(weight, reps)
            st.info(f"**Est 1RM:** {est_1rm:.1f} lbs")
            
            submitted = st.form_submit_button("➕ Add Set", use_container_width=True)
            
            if submitted:
                valid, error_msg = utils.validate_set_input(reps, weight)
                
                if not valid:
                    st.error(error_msg)
                else:
                    st.session_state.last_exercise = selected_exercise
                    st.session_state.last_reps = reps
                    st.session_state.last_weight = weight
                    
                    db.add_set(
                        workout_id,
                        exercise['id'],
                        reps,
                        weight
                    )
                    
                    pr_check = db.check_if_pr(exercise['id'], weight, reps, today.isoformat())
                    
                    if pr_check['is_weight_pr']:
                        st.balloons()
                        st.success(f"🎉 NEW PR! {weight} lbs")
                        db.log_pr(exercise['id'], 'weight', weight, today.isoformat(), f"{reps} reps")
                    
                    if pr_check['is_1rm_pr']:
                        st.balloons()
                        st.success(f"🎉 NEW 1RM PR! {est_1rm:.1f} lbs")
                        db.log_pr(exercise['id'], '1rm', est_1rm, today.isoformat(), f"{weight} lbs x {reps}")
                    
                    if not pr_check['is_weight_pr'] and not pr_check['is_1rm_pr']:
                        st.success(f"✅ {reps} reps @ {weight} lbs")
                    
                    st.rerun()
    
    # Display today's workout
    st.divider()
    st.subheader("Today's Sets")
    
    sets_df = db.get_sets_for_workout(workout_id)
    
    if sets_df.empty:
        st.info("No sets logged yet")
    else:
        for exercise_name in sets_df['exercise'].unique():
            exercise_sets = sets_df[sets_df['exercise'] == exercise_name]
            exercise_obj = db.get_exercise_by_name(exercise_name)
            
            if not exercise_obj:
                st.warning(f"⚠️ Exercise '{exercise_name}' no longer exists")
                continue
            
            with st.expander(f"**{exercise_name}**", expanded=True):
                for idx, row in exercise_sets.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 2, 1])
                    
                    with col1:
                        st.write(f"**Set {row['set_number']}**")
                    with col2:
                        st.write(f"{row['reps']} reps")
                    with col3:
                        st.write(f"{row['weight']} lbs")
                    with col4:
                        volume = row['reps'] * row['weight']
                        est_1rm = calculate_estimated_1rm(row['weight'], row['reps'])
                        st.caption(f"Vol: {volume:,.0f} • 1RM: {est_1rm:.0f}")
                    with col5:
                        if st.button("🗑️", key=f"del_set_{row['id']}", use_container_width=True):
                            db.delete_set(row['id'])
                            st.success("Deleted!")
                            st.rerun()
                
                st.divider()
                
                total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
                max_weight = exercise_sets['weight'].max()
                
                col1, col2 = st.columns(2)
                col1.metric("Total Volume", f"{total_volume:,.0f}")
                col2.metric("Max Weight", f"{max_weight} lbs")

# ==================== HISTORY PAGE ====================

elif page == "History":
    st.title("📅 History")
    
    days_back = st.selectbox("Show last:", [7, 14, 30, 60], index=2)
    
    start_date, end_date = utils.get_date_range(days_back)
    workouts = db.get_workouts_by_date_range(start_date, end_date)
    
    if not workouts:
        st.info(f"No workouts in last {days_back} days")
    else:
        st.caption(f"{len(workouts)} workout(s)")
        
        for workout in workouts:
            workout_details = db.get_workout_details(workout['id'])
            
            expander_title = f"**{utils.format_date(workout['workout_date'])}** - {len(workout_details['sets'])} sets"
            if workout['notes']:
                expander_title += " 📝"
            
            with st.expander(expander_title):
                if workout['notes']:
                    st.markdown(f"""
                    <div class="notes-box">
                        {workout['notes']}
                    </div>
                    """, unsafe_allow_html=True)
                
                if workout_details['sets']:
                    sets_by_exercise = {}
                    for s in workout_details['sets']:
                        ex_name = s['exercise_name']
                        if ex_name not in sets_by_exercise:
                            sets_by_exercise[ex_name] = []
                        sets_by_exercise[ex_name].append(s)
                    
                    for exercise_name, exercise_sets in sets_by_exercise.items():
                        st.markdown(f"**{exercise_name}**")
                        
                        for s in exercise_sets:
                            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                            
                            with col1:
                                st.write(f"**Set {s['set_number']}**")
                            
                            with col2:
                                new_reps = st.number_input(
                                    "Reps",
                                    min_value=1,
                                    max_value=100,
                                    value=s['reps'],
                                    key=f"reps_{s['id']}",
                                    label_visibility="collapsed"
                                )
                            
                            with col3:
                                new_weight = st.number_input(
                                    "Weight",
                                    min_value=0.0,
                                    max_value=1000.0,
                                    value=float(s['weight']),
                                    step=5.0,
                                    key=f"weight_{s['id']}",
                                    label_visibility="collapsed"
                                )
                            
                            with col4:
                                if new_reps != s['reps'] or new_weight != s['weight']:
                                    if st.button("💾", key=f"save_{s['id']}", use_container_width=True):
                                        db.update_set(s['id'], new_reps, new_weight)
                                        st.success("Updated!")
                                        st.rerun()
                                else:
                                    if st.button("🗑️", key=f"del_set_hist_{s['id']}", use_container_width=True):
                                        db.delete_set(s['id'])
                                        st.success("Set deleted!")
                                        st.rerun()
                            
                            volume = new_reps * new_weight
                            est_1rm = calculate_estimated_1rm(new_weight, new_reps)
                            st.caption(f"Vol: {volume:,.0f} • 1RM: {est_1rm:.0f} lbs")
                        
                        st.divider()
                
                with st.expander("✏️ Edit Notes"):
                    current_notes = workout['notes'] if workout['notes'] else ""
                    
                    new_notes = st.text_area(
                        "Workout Notes",
                        value=current_notes,
                        key=f"notes_{workout['id']}",
                        height=100,
                        label_visibility="collapsed"
                    )
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("💾 Save", key=f"save_notes_{workout['id']}", use_container_width=True):
                            db.update_workout_notes(workout['id'], new_notes)
                            st.success("Notes updated!")
                            st.rerun()
                
                st.divider()
                if st.button(f"🗑️ Delete Entire Workout", key=f"del_{workout['id']}", use_container_width=True, type="secondary"):
                    db.delete_workout(workout['id'])
                    st.success("Workout deleted!")
                    st.rerun()

# ==================== MANAGE EXERCISES PAGE ====================

elif page == "Manage Exercises":
    st.title("⚙️ Manage Exercises")
    
    st.subheader("📂 Manage Categories")
    
    with st.form("add_category"):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_category_name = st.text_input("New Category Name", placeholder="e.g., Push Day, Pull Day, Legs")
        with col2:
            st.write("")
            st.write("")
            add_category_btn = st.form_submit_button("➕ Add Category", use_container_width=True)
        
        if add_category_btn:
            if not new_category_name:
                st.error("Please enter a category name")
            else:
                existing_category = db.get_category_by_name(new_category_name)
                if existing_category:
                    st.error("Category already exists")
                else:
                    db.add_category(new_category_name)
                    st.success(f"Added category: {new_category_name}")
                    st.rerun()
    
    categories = db.get_all_categories_cached()
    
    if categories:
        st.write("**Your Categories:**")
        
        num_cols = 3
        for i in range(0, len(categories), num_cols):
            cols = st.columns(num_cols)
            for idx, category in enumerate(categories[i:i+num_cols]):
                with cols[idx]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📁 {category['name']}")
                    with col2:
                        if st.button("🗑️", key=f"del_cat_{category['id']}", use_container_width=True):
                            exercises = db.get_all_exercises_cached()
                            category_in_use = any(e['category'] == category['name'] for e in exercises)
                            
                            if category_in_use:
                                st.error(f"Cannot delete '{category['name']}' - exercises are using it")
                            else:
                                db.delete_category(category['id'])
                                st.success(f"Deleted category: {category['name']}")
                                st.rerun()
    else:
        st.info("No categories yet. Add your first category above!")
    
    st.divider()
    
    st.subheader("💪 Manage Exercises")
    
    with st.form("add_exercise"):
        st.write("**Add New Exercise**")
        
        new_exercise_name = st.text_input("Exercise Name", placeholder="e.g., Bench Press, Squats")
        
        categories = db.get_all_categories_cached()
        if categories is None:
            categories = []
        
        category_names = [c['name'] for c in categories]
        
        if not category_names:
            st.warning("⚠️ Please add at least one category first")
            new_category = None
            submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True, disabled=True)
        else:
            new_category = st.selectbox("Category", category_names)
            submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True)
        
        if submitted:
            if not new_exercise_name:
                st.error("Please enter an exercise name")
            elif not category_names:
                st.error("Please create a category first")
            else:
                existing = db.get_exercise_by_name(new_exercise_name)
                if existing:
                    st.warning(f"✅ '{new_exercise_name}' already exists in your exercises")
                else:
                    db.add_exercise(new_exercise_name, new_category)
                    st.success(f"Added {new_exercise_name}")
                    st.rerun()
    
    st.divider()
    
    st.subheader("Your Exercises")
    exercises = db.get_all_exercises_cached()
    
    if not exercises:
        st.info("No exercises yet. Add your first exercise above!")
    else:
        df = pd.DataFrame(exercises)
        
        for category in category_names:
            category_exercises = df[df['category'] == category]
            
            if not category_exercises.empty:
                with st.expander(f"📁 {category} ({len(category_exercises)})", expanded=True):
                    for _, exercise in category_exercises.iterrows():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"• {exercise['name']}")
                        with col2:
                            if st.button("🗑️", key=f"del_ex_{exercise['id']}", use_container_width=True):
                                db.delete_exercise(exercise['id'])
                                st.success(f"Deleted {exercise['name']}")
                                st.rerun()
        
        orphaned_exercises = df[~df['category'].isin(category_names)]
        if not orphaned_exercises.empty:
            with st.expander(f"⚠️ Uncategorized ({len(orphaned_exercises)})", expanded=False):
                st.warning("These exercises have invalid categories. Consider deleting them.")
                for _, exercise in orphaned_exercises.iterrows():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {exercise['name']} (Category: {exercise['category']})")
                    with col2:
                        if st.button("🗑️", key=f"del_ex_orphan_{exercise['id']}", use_container_width=True):
                            db.delete_exercise(exercise['id'])
                            st.success(f"Deleted {exercise['name']}")
                            st.rerun()
