import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
if 'workout_id' not in st.session_state:
    st.session_state.workout_id = None
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'workout_active' not in st.session_state:
    st.session_state.workout_active = False
if 'workout_date' not in st.session_state:
    st.session_state.workout_date = None

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
    
    .js-plotly-plot .plotly {
        min-height: 300px;
    }
    
    .stForm button[type="submit"] {
        background-color: #667eea;
        color: white;
        font-weight: bold;
        min-height: 3.5rem;
        font-size: 1.2rem;
        margin-top: 1rem;
    }
    
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
    ["📊 Dashboard", "📝 Log Workout", "🏆 PR Records", "📏 Weekly Mileage", "📅 History", "📈 Progress", "⚙️ Manage Exercises"],
    label_visibility="collapsed"
)

page = page.split(" ", 1)[1] if " " in page else page

# ==================== HELPER FUNCTIONS ====================

def get_exercises_by_category(category: str):
    all_exercises = db.get_all_exercises_cached()
    return [e for e in all_exercises if e['category'] == category]

def get_active_categories():
    all_exercises = db.get_all_exercises_cached()
    if not all_exercises:
        return []
    df = pd.DataFrame(all_exercises)
    return df['category'].unique().tolist()

def get_user_categories():
    categories = db.get_all_categories_cached()
    return [c['name'] for c in categories]

def calculate_estimated_1rm(weight: float, reps: int) -> float:
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)

# ==================== DASHBOARD PAGE ====================

if page == "Dashboard":
    st.title("📊 Training Dashboard")
    
    today = get_today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)
    
    st.caption(f"Week of {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}")
    
    this_week_stats = db.get_week_summary(start_of_week.isoformat(), end_of_week.isoformat())
    last_week_stats = db.get_week_summary(start_of_last_week.isoformat(), end_of_last_week.isoformat())
    streak = db.get_workout_streak()
    
    col1, col2 = st.columns(2)
    with col1:
        volume_change = this_week_stats['total_volume'] - last_week_stats['total_volume']
        volume_pct = (volume_change / last_week_stats['total_volume'] * 100) if last_week_stats['total_volume'] > 0 else 0
        col1.metric("Volume", f"{this_week_stats['total_volume']:,.0f} lbs", delta=f"{volume_pct:+.1f}%")
    with col2:
        mileage_change = this_week_stats['total_miles'] - last_week_stats['total_miles']
        col2.metric("Miles", f"{this_week_stats['total_miles']:.1f} mi", delta=f"{mileage_change:+.1f}")
    
    col3, col4 = st.columns(2)
    with col3:
        col3.metric("Workouts", f"{this_week_stats['num_workouts']}", delta=f"{this_week_stats['num_workouts'] - last_week_stats['num_workouts']:+d}")
    with col4:
        if streak > 0:
            col4.markdown(f'<div class="streak-badge">🔥 {streak} Day Streak</div>', unsafe_allow_html=True)
        else:
            days_since = db.get_days_since_last_workout()
            if days_since == 999:
                col4.metric("Last Workout", "None yet")
            else:
                col4.metric("Days Since", f"{days_since}")
    
    st.divider()
    st.subheader("📊 Training Split")
    
    category_volume = db.get_category_volume_this_week(start_of_week.isoformat(), end_of_week.isoformat())
    if not category_volume.empty:
        fig = px.pie(category_volume, values='volume', names='category', title='Volume by Muscle Group', hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No strength training logged this week")
    
    st.divider()
    st.subheader("📈 Volume Trend")
    
    weekly_volume = db.get_weekly_volume_trend(weeks=8)
    if not weekly_volume.empty:
        weekly_volume['week_label'] = weekly_volume.apply(lambda row: f"Wk {row['week']}", axis=1)
        fig = px.bar(weekly_volume, x='week_label', y='volume', title='Last 8 Weeks')
        fig.update_layout(xaxis_title="", yaxis_title="Volume (lbs)", showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for trend")
    
    st.divider()
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
    st.subheader("⚡ Quick Actions")
    st.info("💡 Use the menu (☰) to navigate between pages")

# ==================== LOG WORKOUT PAGE ====================

elif page == "Log Workout":
    st.title("📝 Log Workout")
    
    today = get_today()
    st.caption(f"{today.strftime('%A, %b %d, %Y')}")
    
    if 'last_exercise' not in st.session_state:
        st.session_state.last_exercise = None
    if 'last_reps' not in st.session_state:
        st.session_state.last_reps = 10
    if 'last_weight' not in st.session_state:
        st.session_state.last_weight = 135.0
    
    # CHECK IF WORKOUT IS ACTIVE
    if not st.session_state.workout_active or st.session_state.workout_date != today:
        st.info("👋 Ready to start today's workout?")
        
        existing_workout = db.get_workout_by_date(today.isoformat())
        existing_sets = pd.DataFrame()
        if existing_workout:
            existing_sets = db.get_sets_for_workout(existing_workout['id'])
            if not existing_sets.empty:
                st.warning(f"⚠️ You have {len(existing_sets)} set(s) already logged today")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏋️ Start Workout", use_container_width=True, type="primary"):
                workout_id = db.get_or_create_todays_workout()
                st.session_state.workout_id = workout_id
                st.session_state.workout_active = True
                st.session_state.workout_date = today
                st.success("✅ Workout started!")
                st.rerun()
        with col2:
            if existing_workout and not existing_sets.empty:
                if st.button("📝 Continue Today's Workout", use_container_width=True):
                    st.session_state.workout_id = existing_workout['id']
                    st.session_state.workout_active = True
                    st.session_state.workout_date = today
                    st.success("✅ Workout resumed!")
                    st.rerun()
        
        st.divider()
        st.caption("💡 Start a workout to begin logging sets")

    else:
        # ACTIVE WORKOUT
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success("✅ Workout Active")
        with col2:
            if st.button("🏁 End Workout", use_container_width=True, type="secondary"):
                st.session_state.workout_active = False
                st.session_state.workout_id = None
                st.session_state.workout_date = None
                st.session_state.selected_category = None
                st.success("✅ Workout ended!")
                st.balloons()
                st.rerun()
        
        st.divider()
        
        current_workout = db.get_workout_by_id(st.session_state.workout_id)
        
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
        
        active_categories = get_active_categories()
        
        if not active_categories:
            st.warning("⚠️ No exercises found")
            st.info("Add exercises in ⚙️ Manage Exercises")
        else:
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
            
            if st.session_state.selected_category:
                st.info(f"**Active:** {st.session_state.selected_category}")
                if st.button("❌ Show All", use_container_width=True):
                    st.session_state.selected_category = None
                    st.rerun()
                exercises = get_exercises_by_category(st.session_state.selected_category)
            else:
                exercises = db.get_all_exercises_cached()
            
            st.divider()
            st.subheader("Add Set")
            
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
            
            exercise = db.get_exercise_by_name(selected_exercise)
            
            with st.form(key=f"quick_log_{selected_exercise}", clear_on_submit=False):
                
                today_sets = db.get_sets_for_workout(st.session_state.workout_id)
                
                if not today_sets.empty and 'exercise' in today_sets.columns:
                    todays_sets_for_exercise = today_sets[today_sets['exercise'] == selected_exercise]
                else:
                    todays_sets_for_exercise = pd.DataFrame()
                
                # Determine defaults
                default_weight = 135.0
                default_reps = 10
                
                if exercise:
                    last_session = db.get_last_workout_for_exercise(
                        exercise['id'],
                        before_date=today.isoformat()
                    )
                    
                    if last_session:
                        sets_html = "".join(
                            f"<tr><td style='padding:2px 8px;'>Set {i+1}</td>"
                            f"<td style='padding:2px 8px;'>{s['reps']} reps</td>"
                            f"<td style='padding:2px 8px;'>{s['weight']} lbs</td></tr>"
                            for i, s in enumerate(last_session['sets'])
                        )
                        st.markdown(f"""
                        <div class="last-session">
                            <strong>📊 Last session: {last_session['date']}</strong><br>
                            <table style='margin-top:6px; font-size:0.95rem;'>
                                {sets_html}
                            </table>
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
                
                # Strength inputs
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
                        
                        db.add_set(st.session_state.workout_id, exercise['id'], reps, weight)
                        
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
            
            # Today's sets display
            st.divider()
            st.subheader("Today's Sets")
            
            sets_df = db.get_sets_for_workout(st.session_state.workout_id)
            
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
                        pr_data = db.get_exercise_pr(exercise_obj['id'])
                        max_weight_today = exercise_sets['weight'].max()
                        is_pr_today = False
                        if pr_data['max_weight']:
                            if max_weight_today >= pr_data['max_weight']['max_weight']:
                                is_pr_today = True
                        
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
                        
                        if is_pr_today:
                            st.markdown('<span class="pr-badge">🏆 PR!</span>', unsafe_allow_html=True)

# ==================== PR RECORDS PAGE ====================

elif page == "PR Records":
    st.title("🏆 Personal Records")
    
    tab1, tab2 = st.tabs(["All PRs", "Recent"])
    
    with tab1:
        exercises = db.get_all_exercises_cached()
        if not exercises:
            st.info("No exercises found")
        else:
            strength_exercises = [e for e in exercises if e['category'] not in ["Easy Run", "Tempo Run", "Long Easy Run"]]
            
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
    
    exercises = db.get_all_exercises_cached()
    running_exercises = [e for e in exercises if e['category'] in ["Easy Run", "Tempo Run", "Long Easy Run"]]
    
    if not running_exercises:
        st.info("No running exercises")
    else:
        mileage_data = db.get_weekly_mileage()
        
        if mileage_data.empty:
            st.info("No running data yet")
        else:
            current_week = get_now().isocalendar()[1]
            current_year = get_now().year
            
            current_week_data = mileage_data[(mileage_data['week'] == current_week) & (mileage_data['year'] == current_year)]
            current_miles = current_week_data['total_miles'].iloc[0] if not current_week_data.empty else 0
            
            last_week = current_week - 1 if current_week > 1 else 52
            last_week_year = current_year if current_week > 1 else current_year - 1
            last_week_data = mileage_data[(mileage_data['week'] == last_week) & (mileage_data['year'] == last_week_year)]
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
                st.markdown(f'<div class="info-box">✅ <strong>Safe increase</strong> ({pct_increase:.1f}%)</div>', unsafe_allow_html=True)
            
            st.divider()
            
            mileage_data['week_label'] = mileage_data.apply(lambda row: f"W{row['week']}", axis=1)
            fig = px.bar(mileage_data.tail(12), x='week_label', y='total_miles', title="Last 12 Weeks")
            fig.update_layout(xaxis_title="", yaxis_title="Miles", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

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
                    st.markdown(f'<div class="notes-box">{workout["notes"]}</div>', unsafe_allow_html=True)
                
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
                                new_reps = st.number_input("Reps", min_value=1, max_value=100, value=s['reps'], key=f"reps_{s['id']}", label_visibility="collapsed")
                            with col3:
                                new_weight = st.number_input("Weight", min_value=0.0, max_value=1000.0, value=float(s['weight']), step=5.0, key=f"weight_{s['id']}", label_visibility="collapsed")
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
                    new_notes = st.text_area("Workout Notes", value=current_notes, key=f"notes_{workout['id']}", height=100, label_visibility="collapsed")
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

# ==================== PROGRESS PAGE ====================

elif page == "Progress":
    st.title("📈 Progress")
    
    exercises = db.get_all_exercises_cached()
    
    if not exercises:
        st.warning("No exercises found")
    else:
        exercise_names = [e['name'] for e in exercises]
        selected_exercise_name = st.selectbox("Exercise", exercise_names)
        
        exercise = db.get_exercise_by_name(selected_exercise_name)
        
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
            fig = px.line(max_weight_df, x='workout_date', y='weight', markers=True, title="Weight Progress")
            fig.update_layout(xaxis_title="", yaxis_title="Weight (lbs)", height=350)
            st.plotly_chart(fig, use_container_width=True)

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
        
        category_names = [c['name'] for c in categories] if categories else []
        
        if not category_names:
            st.warning("⚠️ Please add at least one category first")
            new_category = None
        else:
            new_category = st.selectbox("Category", category_names)
        
        if st.form_submit_button("➕ Add Exercise", use_container_width=True):
            if not new_exercise_name:
                st.error("Please enter an exercise name")
            elif not category_names:
                st.error("Please create a category first")
            else:
                existing = db.get_exercise_by_name(new_exercise_name)
                if existing:
                    st.error("Exercise already exists")
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
        category_names = [c['name'] for c in categories] if categories else []
        
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

# Footer
st.sidebar.divider()
st.sidebar.caption("Optimized for mobile")
