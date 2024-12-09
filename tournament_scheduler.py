import streamlit as st
import itertools
from datetime import datetime, timedelta
import pandas as pd
import random

# Constants
grounds = ["Off_Stump", "Middle_Stump", "Leg_Stump"]
time_slots = ["Morning", "Afternoon", "Evening", "Night"]
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Generate round-robin pairs
def generate_round_robin(teams):
    return list(itertools.combinations(teams, 2))

# Assign least-used ground
def assign_ground(grounds_played, date, ground_usage):
    available_grounds = [ground for ground in grounds if ground_usage[date][ground] < 1]
    return min(available_grounds, key=lambda ground: grounds_played.get(ground, 0)) if available_grounds else None

# Check matches per week with specific logic
def can_schedule_match_this_week(team, date, matches_played, max_matches_per_week):
    week_start = date - timedelta(days=date.weekday())
    week_end = week_start + timedelta(days=6)
    week_matches = matches_played[team].get((week_start, week_end), 0)
    return week_matches < max_matches_per_week

# Main scheduling function with improved day distribution logic
def schedule_matches(start_date, end_date, teams, teams_preferences, max_matches_per_week):
    schedule = []
    match_pairs = generate_round_robin(teams)
    ground_availability = {start_date + timedelta(days=x): time_slots[:] for x in range((end_date - start_date).days + 1)}
    ground_usage = {start_date + timedelta(days=x): {ground: 0 for ground in grounds} for x in range((end_date - start_date).days + 1)}

    # Track ground and day usage, matches, and last match date
    grounds_played = {team: {ground: 0 for ground in grounds} for team in teams}
    days_played = {team: {day: 0 for day in days_of_week} for team in teams}
    matches_played = {team: {} for team in teams}

    # Step 1: Prioritize distribution of matches across multiple preferred days
    unscheduled_matches = []
    for pair in match_pairs:
        scheduled = False
        team1_days = list(teams_preferences[pair[0]].keys())
        team2_days = list(teams_preferences[pair[1]].keys())
        common_days = list(set(team1_days) & set(team2_days))
        
        # Sort days by usage to prioritize the least-used days
        random.shuffle(common_days)  # Add randomness to avoid bias
        sorted_days = sorted(common_days, key=lambda day: days_played[pair[0]].get(day, 0) + days_played[pair[1]].get(day, 0))
        
        for day in sorted_days:
            for date in ground_availability.keys():
                if date.strftime("%A") == day:
                    if (
                        date.strftime("%Y-%m-%d") not in teams_preferences[pair[0]]["exceptions"]
                        and date.strftime("%Y-%m-%d") not in teams_preferences[pair[1]]["exceptions"]
                        and can_schedule_match_this_week(pair[0], date, matches_played, max_matches_per_week)
                        and can_schedule_match_this_week(pair[1], date, matches_played, max_matches_per_week)
                    ):
                        team1_slots = teams_preferences[pair[0]].get(day, [])
                        team2_slots = teams_preferences[pair[1]].get(day, [])
                        available_slots = set(ground_availability[date]) & set(team1_slots) & set(team2_slots)

                        if available_slots:
                            slot = random.choice(list(available_slots))
                            ground = assign_ground(grounds_played[pair[0]], date, ground_usage)
                            if ground:
                                grounds_played[pair[0]][ground] += 1
                                grounds_played[pair[1]][ground] += 1
                                ground_usage[date][ground] += 1

                                # Schedule match
                                schedule.append({
                                    "team1": pair[0],
                                    "team2": pair[1],
                                    "ground": ground,
                                    "date": date.strftime("%Y-%m-%d"),
                                    "day": day,
                                    "slot": slot
                                })

                                ground_availability[date].remove(slot)
                                week_start = date - timedelta(days=date.weekday())
                                matches_played[pair[0]][(week_start, week_start + timedelta(days=6))] = matches_played[pair[0]].get((week_start, week_start + timedelta(days=6)), 0) + 1
                                matches_played[pair[1]][(week_start, week_start + timedelta(days=6))] = matches_played[pair[1]].get((week_start, week_start + timedelta(days=6)), 0) + 1
                                days_played[pair[0]][day] += 1
                                days_played[pair[1]][day] += 1
                                scheduled = True
                                break
                if scheduled:
                    break
            if scheduled:
                break

        if not scheduled:
            unscheduled_matches.append(pair)

    # Step 2: Fallback logic for unscheduled matches
    for pair in unscheduled_matches:
        for date in ground_availability.keys():
            day_name = date.strftime("%A")
            team1_slots = teams_preferences[pair[0]].get(day_name, [])
            team2_slots = teams_preferences[pair[1]].get(day_name, [])
            available_slots = set(ground_availability[date]) & set(team1_slots) & set(team2_slots)

            if available_slots:
                slot = random.choice(list(available_slots))
                ground = assign_ground(grounds_played[pair[0]], date, ground_usage)
                if ground:
                    schedule.append({
                        "team1": pair[0],
                        "team2": pair[1],
                        "ground": ground,
                        "date": date.strftime("%Y-%m-%d"),
                        "day": day_name,
                        "slot": slot
                    })

                    break

    return schedule

# CSV creation
def create_csv(schedule):
    df = pd.DataFrame(schedule)
    df.columns = ["Team 1", "Team 2", "Ground", "Date", "Day", "Slot"]
    csv = df.to_csv(index=False)
    return csv

# Streamlit UI
def main():
    st.set_page_config(page_title="Cricket Tournament Scheduler", layout="wide", initial_sidebar_state="expanded")
    st.title("🏏 Cricket Tournament Scheduler")
    st.header("Tournament Setup")

    start_date = st.date_input("Select Tournament Start Date", datetime.now())
    end_date = st.date_input("Select Tournament End Date", datetime.now() + timedelta(days=30))

    num_teams = st.number_input("Number of teams", min_value=2, max_value=16, value=8, step=1)

    teams = []
    for i in range(num_teams):
        team_name = st.text_input(f"Enter name for Team {i+1}", f"Team {chr(65 + i)}", key=f"team_{i}")
        teams.append(team_name)

    max_matches_per_week = st.number_input("Maximum matches per week", min_value=1, max_value=2, value=1, step=1)

    st.header("Team Preferences")
    teams_preferences = {}

    for team in teams:
        st.subheader(f"⚙️ {team}'s Preferences")
        team_pref = {}
        for day in days_of_week:
            slots = st.multiselect(f"Select slots for {team} on {day}", time_slots, key=f"{team}_{day}")
            team_pref[day] = slots

        exceptions = st.text_area(f"Enter exception dates for {team} (YYYY-MM-DD, comma-separated)", "", key=f"{team}_exceptions")
        exception_days = [date.strip() for date in exceptions.split(",") if date.strip()]

        teams_preferences[team] = {day: team_pref[day] for day in days_of_week if team_pref[day]}
        teams_preferences[team]["exceptions"] = exception_days

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("📅 Generate Schedule"):
            schedule = schedule_matches(start_date, end_date, teams, teams_preferences, max_matches_per_week)
            csv = create_csv(schedule)
            st.download_button(label="💾 Download Schedule as CSV", data=csv, file_name="tournament_schedule.csv", mime="text/csv")
    
    with col2:
        if st.button("🔄 Reset"):
            st.experimental_rerun()

if __name__ == "__main__":
    main()
