import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import database as db
import utils

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
if 'workout_id' not in st.session_state:
    st.session_state.workout_id = db.get_or_create_todays_workout()
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

# Custom CSS for mobile optimization
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
    
    /* Responsive metric cards */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.5rem, 4vw, 2.5rem);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: clamp(0.875rem, 2.5vw, 1rem);
    }
    
    /* Mobile-friendly tables */
    .dataframe {
        font-size: 0.9rem;
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
        /* COMPLETELY hide sidebar when collapsed on mobile */
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
        
        /* Hide the sidebar container completely when closed */
        section[data-testid="stSidebar"] > div:first-child {
            width: 80vw;
        }
        
        /* Make sure main content uses full width */
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            max-width: 100%;
        }
        
        /* Remove any sidebar remnants */
        [data-testid="collapsedControl"] {
            position: fixed;
            top: 0.5rem;
            left: 0.5rem;
            z-index: 1000;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
            margin-bottom: 0.5rem;
        }
        
        /* Larger titles on mobile */
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.25rem !important;
        }
        
        /* Form spacing */
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
    .success-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
        margin: 0.5rem 0;
        font-size: 1rem;
    }
    
    .pr-badge {
        background-color: #ffd700;
        color: #000;
        padding: 0.4rem 0.75rem;
        border-radius: 0.3rem;
        font-weight: bold;
        font-size: 1rem;
    }
    
    .last-session {
        background-color: #e7f3ff;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196F3;
        margin: 0.75rem 0;
        font-size: 1rem;
    }
    
    .category-button {
        background-color: #f0f2f6;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.25rem;
        min-height: 3rem;
    }
    
    .pr-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.25rem;
        border-radius: 0.5rem;
        margin: 0.75rem 0;
    }
    
    .recent-pr {
        background-color: #fff3cd;
        border-left: 4px solid #ffd700;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0.5rem;
        font-size: 1rem;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0.5rem;
        font-size: 1rem;
    }
    
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0.5rem;
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
    
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .streak-badge {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.75rem 1.25rem;
        border-radius: 2rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem 0;
        font-size: 1.1rem;
    }
    
    /* Larger tap targets for charts */
    .js-plotly-plot .plotly {
        min-height: 300px;
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

# Sidebar navigation with mobile-friendly icons
# st.sidebar.title("💪 Workout Tracker")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📝 Log Workout", "🏆 PR Records", "📏 Weekly Mileage", "📅 History", "📈 Progress", "⚙️ Manage Exercises"],
    label_visibility="collapsed"
)

# Clean up page names (remove emojis for internal use)
page = page.split(" ", 1)[1] if " " in page else page

# ==================== HELPER FUNCTIONS ====================

def get_exercises_by_category(category: str):
    """Get all exercises for a specific category"""
    all_exercises = db.get_all_exercises()
    return [e for e in all_exercises if e['category'] == category]

def get_active_categories():
    """Get categories that have at least one exercise"""
    all_exercises = db.get_all_exercises()
    if not all_exercises:
        return []
    
    df = pd.DataFrame(all_exercises)
    return df['category'].unique().tolist()

def calculate_estimated_1rm(weight: float, reps: int) -> float:
    """Calculate estimated 1RM using Epley formula"""
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)

# ==================== DASHBOARD PAGE ====================

if page == "Dashboard":
    st.title("📊 Training Dashboard")
    
    # Get current week dates
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get last week dates
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)
    
    st.caption(f"Week of {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}")
    
    # Get weekly stats
    this_week_stats = db.get_week_summary(start_of_week.isoformat(), end_of_week.isoformat())
    last_week_stats = db.get_week_summary(start_of_last_week.isoformat(), end_of_last_week.isoformat())
    
    # Get workout streak
    streak = db.get_workout_streak()
    
    # Top row - Key metrics (mobile will stack these)
    col1, col2 = st.columns(2)
    
    with col1:
        volume_change = this_week_stats['total_volume'] - last_week_stats['total_volume']
        volume_pct = (volume_change / last_week_stats['total_volume'] * 100) if last_week_stats['total_volume'] > 0 else 0
        col1.metric(
            "Volume",
            f"{this_week_stats['total_volume']:,.0f} lbs",
            delta=f"{volume_pct:+.1f}%"
        )
    
    with col2:
        mileage_change = this_week_stats['total_miles'] - last_week_stats['total_miles']
        col2.metric(
            "Miles",
            f"{this_week_stats['total_miles']:.1f} mi",
            delta=f"{mileage_change:+.1f}"
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        col3.metric(
            "Workouts",
            f"{this_week_stats['num_workouts']}",
            delta=f"{this_week_stats['num_workouts'] - last_week_stats['num_workouts']:+d}"
        )
    
    with col4:
        if streak > 0:
            col4.markdown(f"""
            <div class="streak-badge">
                🔥 {streak} Day Streak
            </div>
            """, unsafe_allow_html=True)
        else:
            days_since = db.get_days_since_last_workout()
            if days_since == 999:
                col4.metric("Last Workout", "None yet")
            else:
                col4.metric("Days Since", f"{days_since}")
    
    st.divider()
    
    # Charts section
    st.subheader("📊 Training Split")
    
    category_volume = db.get_category_volume_this_week(start_of_week.isoformat(), end_of_week.isoformat())
    
    if not category_volume.empty:
        fig = px.pie(
            category_volume,
            values='volume',
            names='category',
            title='Volume by Muscle Group',
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No strength training logged this week")
    
    st.divider()
    
    st.subheader("📈 Volume Trend")
    
    weekly_volume = db.get_weekly_volume_trend(weeks=8)
    
    if not weekly_volume.empty:
        weekly_volume['week_label'] = weekly_volume.apply(
            lambda row: f"Wk {row['week']}", axis=1
        )
        
        fig = px.bar(
            weekly_volume,
            x='week_label',
            y='volume',
            title='Last 8 Weeks'
        )
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Volume (lbs)",
            showlegend=False,
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for trend")
    
    st.divider()
    
    # Recent PRs
    st.subheader("🏆 Recent PRs")
    
    recent_prs = db.get_recent_prs(days=7)
    
    if not recent_prs:
        st.info("No PRs in the last 7 days")
    else:
        for pr in recent_prs[:3]:
            st.markdown(f"""
            <div class="recent-pr">
                <strong>{pr['exercise_name']}</strong> - {pr['pr_type'].upper()}<br>
                <strong>{pr['value']:.1f}</strong> {pr['context']}<br>
                <small>{pr['achieved_date']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    st.info("💡 Use the menu (☰) to navigate between pages")

# ==================== LOG WORKOUT PAGE ====================

elif page == "Log Workout":
    st.title("📝 Log Workout")
    
    # Get today's date
    today = datetime.now().date()
    st.caption(f"{today.strftime('%A, %b %d, %Y')}")
    
    # Initialize session state for last logged set
    if 'last_exercise' not in st.session_state:
        st.session_state.last_exercise = None
    if 'last_reps' not in st.session_state:
        st.session_state.last_reps = 10
    if 'last_weight' not in st.session_state:
        st.session_state.last_weight = 135.0
    if 'last_miles' not in st.session_state:
        st.session_state.last_miles = 3.0
    if 'last_time' not in st.session_state:
        st.session_state.last_time = 30.0
    if 'last_hr' not in st.session_state:
        st.session_state.last_hr = 140
    
    # Get current workout details
    current_workout = db.get_workout_by_id(st.session_state.workout_id)
    
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
            db.update_workout_notes(st.session_state.workout_id, notes)
            st.success("Notes saved!")
    
    # Get categories with exercises
    active_categories = get_active_categories()
    
    if not active_categories:
        st.warning("⚠️ No exercises found")
        st.info("Add exercises in ⚙️ Manage Exercises")
    else:
        # Quick Start
        st.subheader("🚀 Quick Start")
        
        ordered_categories = [
            ("Lower Strength", "Mon - Lower"),
            ("Easy Run", "Tue - Easy Run"),
            ("Upper Strength", "Wed - Upper"),
            ("Tempo Run", "Thu - Tempo"),
            ("Lower Volume / Hypertrophy", "Fri - Lower Vol"),
            ("Upper Volume / Hypertrophy", "Sat - Upper Vol"),
            ("Long Easy Run", "Sun - Long Run"),
        ]
        
        available_categories = [
            (cat, label) for cat, label in ordered_categories 
            if cat in active_categories
        ]
        
        if available_categories:
            num_cols = 2
            for i in range(0, len(available_categories), num_cols):
                cols = st.columns(num_cols)
                
                for idx, (category, label) in enumerate(available_categories[i:i+num_cols]):
                    with cols[idx]:
                        if st.button(label, key=f"cat_{category}", use_container_width=True):
                            st.session_state.selected_category = category
                            st.success(f"✓ {category}")
                            st.rerun()
        
        # Show selected category
        if st.session_state.selected_category:
            st.info(f"**Active:** {st.session_state.selected_category}")
            if st.button("❌ Show All", use_container_width=True):
                st.session_state.selected_category = None
                st.rerun()
            
            exercises = get_exercises_by_category(st.session_state.selected_category)
        else:
            exercises = db.get_all_exercises()
        
        st.divider()
        
        # Quick add form - mobile optimized
        st.divider()
        
        # Exercise selector OUTSIDE the form
        st.subheader("Add Set")
        
        exercise_names = [e['name'] for e in exercises]
        
        # Set default index based on last exercise
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
        
        # Determine if this is a running exercise
        is_running = exercise and exercise['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]
        
        # Quick add form - mobile optimized
        # Force form to reset when exercise changes by using exercise name in form key
        with st.form(key=f"quick_log_{selected_exercise}", clear_on_submit=False):
            
            # Show last session data
            if exercise:
                last_session = db.get_last_workout_for_exercise(
                    exercise['id'],
                    before_date=today.isoformat()
                )
                
                if last_session:
                    if is_running:
                        last_miles = last_session['sets'][0]['reps'] / 10.0
                        last_time = last_session['sets'][0]['weight']
                        last_hr = last_session['sets'][0]['set_number']
                        pace = last_time / last_miles if last_miles > 0 else 0
                        
                        st.markdown(f"""
                        <div class="last-session">
                            <strong>📊 Last: {last_session['date']}</strong><br>
                            {last_miles:.1f} mi • {last_time:.0f} min • {int(pace)}:{int((pace % 1) * 60):02d}/mi
                            {f' • {last_hr} bpm' if last_hr > 0 else ''}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Use last session values when switching exercises
                        default_miles = last_miles
                        default_time = last_time
                        default_hr = last_hr if last_hr > 0 else 140
                    else:
                        st.markdown(f"""
                        <div class="last-session">
                            <strong>📊 Last: {last_session['date']}</strong><br>
                            {len(last_session['sets'])} sets • 
                            {last_session['sets'][0]['reps']}-{last_session['sets'][-1]['reps']} reps • 
                            {last_session['sets'][0]['weight']}-{max(s['weight'] for s in last_session['sets'])} lbs
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Use last session values when switching exercises
                        default_weight = max(s['weight'] for s in last_session['sets'])
                        default_reps = last_session['sets'][0]['reps']
                else:
                    # No previous session - use defaults
                    if is_running:
                        default_miles = 3.0
                        default_time = 30.0
                        default_hr = 140
                    else:
                        default_weight = 135.0
                        default_reps = 10
            else:
                # No exercise selected - use defaults
                default_weight = 135.0
                default_reps = 10
                default_miles = 3.0
                default_time = 30.0
                default_hr = 140
            
            # Input fields
            if is_running:
                # RUNNING INPUTS
                miles = st.number_input("Miles", min_value=0.1, max_value=50.0, value=default_miles, step=0.1)
                
                time_minutes = st.number_input("Time (min)", min_value=1.0, max_value=500.0, value=default_time, step=1.0)
                
                heart_rate = st.number_input("Avg HR (bpm)", min_value=0, max_value=220, value=default_hr, step=1)
                
                # Show pace
                if miles > 0:
                    pace = time_minutes / miles
                    st.info(f"**Pace:** {int(pace)}:{int((pace % 1) * 60):02d} min/mile")
                
                submitted = st.form_submit_button("➕ Add Run", use_container_width=True)
                
                if submitted:
                    if miles <= 0:
                        st.error("Miles must be positive")
                    elif time_minutes <= 0:
                        st.error("Time must be positive")
                    else:
                        # Save to session state
                        st.session_state.last_exercise = selected_exercise
                        st.session_state.last_miles = miles
                        st.session_state.last_time = time_minutes
                        st.session_state.last_hr = heart_rate
                        
                        db.add_set(
                            st.session_state.workout_id,
                            exercise['id'],
                            int(miles * 10),
                            time_minutes
                        )
                        
                        db.update_last_set_hr(st.session_state.workout_id, exercise['id'], heart_rate)
                        
                        pr_check = db.check_running_pr(exercise['id'], miles, time_minutes, today.isoformat())
                        
                        if pr_check['is_pace_pr']:
                            st.balloons()
                            st.success(f"🎉 NEW PACE PR! {int(pace)}:{int((pace % 1) * 60):02d}")
                        elif pr_check['is_distance_pr']:
                            st.balloons()
                            st.success(f"🎉 NEW DISTANCE PR! {miles} miles")
                        else:
                            st.success(f"✅ {miles} mi • {time_minutes:.0f} min")
                        
                        st.rerun()
            
            else:
                # STRENGTH TRAINING INPUTS
                reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps, step=1)
                
                weight = st.number_input("Weight (lbs)", min_value=0.0, max_value=1000.0, value=default_weight, step=5.0)
                
                # Show estimated 1RM
                est_1rm = calculate_estimated_1rm(weight, reps)
                st.info(f"**Est 1RM:** {est_1rm:.1f} lbs")
                
                submitted = st.form_submit_button("➕ Add Set", use_container_width=True)
                
                if submitted:
                    valid, error_msg = utils.validate_set_input(reps, weight)
                    
                    if not valid:
                        st.error(error_msg)
                    else:
                        # Save to session state
                        st.session_state.last_exercise = selected_exercise
                        st.session_state.last_reps = reps
                        st.session_state.last_weight = weight
                        
                        db.add_set(
                            st.session_state.workout_id,
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
        
        sets_df = db.get_sets_for_workout(st.session_state.workout_id)
        
        if sets_df.empty:
            st.info("No sets logged yet")
        else:
            # Group by exercise
            for exercise_name in sets_df['exercise'].unique():
                exercise_sets = sets_df[sets_df['exercise'] == exercise_name]
                exercise_obj = db.get_exercise_by_name(exercise_name)
                
                is_running_exercise = exercise_obj['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]
                
                with st.expander(f"**{exercise_name}**", expanded=True):
                    if is_running_exercise:
                        # Running sets with delete buttons
                        for idx, row in exercise_sets.iterrows():
                            miles = row['reps'] / 10.0
                            time_min = row['weight']
                            pace = time_min / miles if miles > 0 else 0
                            hr = row['set_number']
                            
                            col1, col2 = st.columns([5, 1])
                            with col1:
                                st.write(f"**{miles:.1f} mi** • {time_min:.0f} min • {int(pace)}:{int((pace % 1) * 60):02d}/mi" + (f" • {hr} bpm" if hr > 0 else ""))
                            with col2:
                                if st.button("🗑️", key=f"del_set_{row['id']}", use_container_width=True):
                                    db.delete_set(row['id'])
                                    st.success("Deleted!")
                                    st.rerun()
                    else:
                        # Strength training sets
                        pr_data = db.get_exercise_pr(exercise_obj['id'])
                        max_weight_today = exercise_sets['weight'].max()
                        is_pr_today = False
                        
                        if pr_data['max_weight']:
                            if max_weight_today >= pr_data['max_weight']['max_weight']:
                                is_pr_today = True
                        
                        # Display sets with delete buttons
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
                        
                        # Summary stats
                        total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
                        max_weight = exercise_sets['weight'].max()
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Total Volume", f"{total_volume:,.0f}")
                        col2.metric("Max Weight", f"{max_weight} lbs")
                        
                        if is_pr_today:
                            st.markdown('<span class="pr-badge">🏆 PR!</span>', unsafe_allow_html=True)

# ==================== PR RECORDS PAGE ====================

elif page == "PR Records":
    st.title("🏆 Personal Records")
    
    tab1, tab2 = st.tabs(["All PRs", "Recent"])
    
    with tab1:
        exercises = db.get_all_exercises()
        
        if not exercises:
            st.info("No exercises found")
        else:
            strength_exercises = [e for e in exercises if e['category'] not in ["Easy Run", "Tempo Run", "Long Easy Run"]]
            running_exercises = [e for e in exercises if e['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]]
            
            if strength_exercises:
                st.markdown("### 💪 Strength PRs")
                
                pr_data = []
                for exercise in strength_exercises:
                    prs = db.get_exercise_pr(exercise['id'])
                    
                    if prs['max_weight']:
                        pr_data.append({
                            'Exercise': exercise['name'],
                            'Max': f"{prs['max_weight']['max_weight']:.0f} lbs",
                            'Date': prs['max_weight']['workout_date']
                        })
                
                if pr_data:
                    df = pd.DataFrame(pr_data)
                    st.dataframe(df, hide_index=True, use_container_width=True)
            
            if running_exercises:
                st.divider()
                st.markdown("### 🏃 Running PRs")
                
                run_pr_data = []
                for exercise in running_exercises:
                    prs = db.get_running_prs(exercise['id'])
                    
                    if prs['fastest_pace']:
                        pace = prs['fastest_pace']['pace']
                        run_pr_data.append({
                            'Type': exercise['name'],
                            'Pace': f"{int(pace)}:{int((pace % 1) * 60):02d}",
                            'Date': prs['fastest_pace']['date']
                        })
                
                if run_pr_data:
                    df = pd.DataFrame(run_pr_data)
                    st.dataframe(df, hide_index=True, use_container_width=True)
    
    with tab2:
        st.subheader("Last 30 Days")
        
        recent_prs = db.get_recent_prs(days=30)
        
        if not recent_prs:
            st.info("No PRs in last 30 days")
        else:
            for pr in recent_prs[:5]:
                st.markdown(f"""
                <div class="recent-pr">
                    <strong>🏆 {pr['exercise_name']}</strong><br>
                    <strong>{pr['value']:.1f}</strong> {pr['context']}<br>
                    <small>{pr['achieved_date']}</small>
                </div>
                """, unsafe_allow_html=True)

# ==================== WEEKLY MILEAGE PAGE ====================

elif page == "Weekly Mileage":
    st.title("📏 Weekly Mileage")
    
    exercises = db.get_all_exercises()
    running_exercises = [e for e in exercises if e['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]]
    
    if not running_exercises:
        st.info("No running exercises")
    else:
        mileage_data = db.get_weekly_mileage()
        
        if mileage_data.empty:
            st.info("No running data yet")
        else:
            current_week = datetime.now().isocalendar()[1]
            current_year = datetime.now().year
            
            current_week_data = mileage_data[
                (mileage_data['week'] == current_week) & 
                (mileage_data['year'] == current_year)
            ]
            
            current_miles = current_week_data['total_miles'].iloc[0] if not current_week_data.empty else 0
            
            last_week = current_week - 1 if current_week > 1 else 52
            last_week_year = current_year if current_week > 1 else current_year - 1
            
            last_week_data = mileage_data[
                (mileage_data['week'] == last_week) & 
                (mileage_data['year'] == last_week_year)
            ]
            
            last_week_miles = last_week_data['total_miles'].iloc[0] if not last_week_data.empty else 0
            
            pct_increase = ((current_miles - last_week_miles) / last_week_miles * 100) if last_week_miles > 0 else 0
            
            col1, col2 = st.columns(2)
            
            col1.metric("This Week", f"{current_miles:.1f} mi")
            col2.metric("Last Week", f"{last_week_miles:.1f} mi")
            
            col3, col4 = st.columns(2)
            col3.metric("Change", f"{pct_increase:+.1f}%")
            
            recent_4_weeks = mileage_data.tail(4)
            avg_4_weeks = recent_4_weeks['total_miles'].mean()
            col4.metric("4-Wk Avg", f"{avg_4_weeks:.1f} mi")
            
            if pct_increase > 10 and last_week_miles > 0:
                st.markdown(f"""
                <div class="warning-box">
                    ⚠️ <strong>Injury Risk!</strong><br>
                    +{pct_increase:.1f}% increase. Consider scaling back to {last_week_miles * 1.1:.1f} mi
                </div>
                """, unsafe_allow_html=True)
            elif pct_increase > 0 and last_week_miles > 0:
                st.markdown(f"""
                <div class="info-box">
                    ✅ <strong>Safe increase</strong> ({pct_increase:.1f}%)
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            mileage_data['week_label'] = mileage_data.apply(
                lambda row: f"W{row['week']}", axis=1
            )
            
            fig = px.bar(
                mileage_data.tail(12),
                x='week_label',
                y='total_miles',
                title="Last 12 Weeks"
            )
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Miles",
                showlegend=False,
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

# ==================== HISTORY PAGE ====================

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
                # Notes section
                if workout['notes']:
                    st.markdown(f"""
                    <div class="notes-box">
                        {workout['notes']}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display sets
                if workout_details['sets']:
                    # Group sets by exercise
                    sets_by_exercise = {}
                    for s in workout_details['sets']:
                        ex_name = s['exercise_name']
                        if ex_name not in sets_by_exercise:
                            sets_by_exercise[ex_name] = []
                        sets_by_exercise[ex_name].append(s)
                    
                    # Display each exercise
                    for exercise_name, exercise_sets in sets_by_exercise.items():
                        st.markdown(f"**{exercise_name}**")
                        
                        # Check if running exercise
                        is_running = exercise_sets[0]['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]
                        
                        if is_running:
                            # Display running sets
                            for s in exercise_sets:
                                miles = s['reps'] / 10.0
                                time_min = s['weight']
                                pace = time_min / miles if miles > 0 else 0
                                hr = s['set_number']
                                
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    st.write(f"{miles:.1f} mi • {time_min:.0f} min • {int(pace)}:{int((pace % 1) * 60):02d}/mi" + (f" • {hr} bpm" if hr > 0 else ""))
                                with col2:
                                    if st.button("🗑️", key=f"del_set_hist_{s['id']}", use_container_width=True):
                                        db.delete_set(s['id'])
                                        st.success("Set deleted!")
                                        st.rerun()
                        else:
                            # Display strength sets with edit capability
                            for s in exercise_sets:
                                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                                
                                with col1:
                                    st.write(f"**Set {s['set_number']}**")
                                
                                with col2:
                                    # Editable reps
                                    new_reps = st.number_input(
                                        "Reps",
                                        min_value=1,
                                        max_value=100,
                                        value=s['reps'],
                                        key=f"reps_{s['id']}",
                                        label_visibility="collapsed"
                                    )
                                
                                with col3:
                                    # Editable weight
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
                                    # Save/Delete buttons
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
                                
                                # Show volume and 1RM
                                volume = new_reps * new_weight
                                est_1rm = calculate_estimated_1rm(new_weight, new_reps)
                                st.caption(f"Vol: {volume:,.0f} • 1RM: {est_1rm:.0f} lbs")
                        
                        st.divider()
                
                # Edit notes button
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
                
                # Delete entire workout
                st.divider()
                if st.button(f"🗑️ Delete Entire Workout", key=f"del_{workout['id']}", use_container_width=True, type="secondary"):
                    db.delete_workout(workout['id'])
                    st.success("Workout deleted!")
                    st.rerun()

# ==================== PROGRESS PAGE ====================

elif page == "Progress":
    st.title("📈 Progress")
    
    exercises = db.get_all_exercises()
    
    if not exercises:
        st.warning("No exercises found")
    else:
        exercise_names = [e['name'] for e in exercises]
        selected_exercise_name = st.selectbox("Exercise", exercise_names)
        
        exercise = db.get_exercise_by_name(selected_exercise_name)
        is_running = exercise['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]
        
        if is_running:
            running_df = db.get_running_stats(exercise['id'])
            
            if running_df.empty:
                st.info("No data yet")
            else:
                col1, col2 = st.columns(2)
                col1.metric("Runs", len(running_df))
                col2.metric("Miles", f"{running_df['miles'].sum():.1f}")
                
                col3, col4 = st.columns(2)
                avg_pace = running_df['pace_min_per_mile'].mean()
                col3.metric("Avg Pace", f"{int(avg_pace)}:{int((avg_pace % 1) * 60):02d}")
                
                if running_df['heart_rate'].mean() > 0:
                    col4.metric("Avg HR", f"{running_df['heart_rate'].mean():.0f}")
                
                st.divider()
                
                fig = px.line(
                    running_df,
                    x='workout_date',
                    y='pace_min_per_mile',
                    markers=True,
                    title="Pace Trend"
                )
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="Pace (min/mi)",
                    yaxis_autorange="reversed",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            pr_data = db.get_exercise_pr(exercise['id'])
            
            if pr_data['max_weight']:
                col1, col2 = st.columns(2)
                col1.metric("Max Weight", f"{pr_data['max_weight']['max_weight']:.0f} lbs")
                
                if pr_data['max_volume']:
                    col2.metric("Max Volume", f"{pr_data['max_volume']['max_volume']:,.0f}")
            
            st.divider()
            
            progress_df = db.get_exercise_progress(exercise['id'], limit=200)
            
            if not progress_df.empty:
                max_weight_df = progress_df.groupby('workout_date')['weight'].max().reset_index()
                
                fig = px.line(
                    max_weight_df,
                    x='workout_date',
                    y='weight',
                    markers=True,
                    title="Weight Progress"
                )
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="Weight (lbs)",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

# ==================== MANAGE EXERCISES PAGE ====================

elif page == "Manage Exercises":
    st.title("⚙️ Manage Exercises")
    
    with st.form("add_exercise"):
        st.subheader("Add Exercise")
        
        new_exercise_name = st.text_input("Name")
        new_category = st.selectbox("Category", utils.CATEGORIES)
        
        if st.form_submit_button("➕ Add", use_container_width=True):
            if not new_exercise_name:
                st.error("Enter a name")
            else:
                existing = db.get_exercise_by_name(new_exercise_name)
                if existing:
                    st.error("Already exists")
                else:
                    db.add_exercise(new_exercise_name, new_category)
                    st.success(f"Added {new_exercise_name}")
                    st.rerun()
    
    st.divider()
    
    st.subheader("Your Exercises")
    exercises = db.get_all_exercises()
    
    if not exercises:
        st.info("No exercises yet")
    else:
        df = pd.DataFrame(exercises)
        
        for category in utils.CATEGORIES:
            category_exercises = df[df['category'] == category]
            
            if not category_exercises.empty:
                with st.expander(f"{category} ({len(category_exercises)})"):
                    for _, exercise in category_exercises.iterrows():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"• {exercise['name']}")
                        with col2:
                            if st.button("🗑️", key=f"del_{exercise['id']}", use_container_width=True):
                                db.delete_exercise(exercise['id'])
                                st.rerun()

# Footer
st.sidebar.divider()
# st.sidebar.caption("💪 Workout Tracker")
st.sidebar.caption("Optimized for mobile")
