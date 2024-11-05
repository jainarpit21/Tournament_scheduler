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

# Choose the least-used day from selected days for balanced distribution
def choose_least_used_day(selected_days, days_played):
    available_days = [(day, days_played.get(day, 0)) for day in selected_days]
    random.shuffle(available_days)  # Randomize to avoid bias
    return min(available_days, key=lambda x: x[1])[0]

# Check matches per week with specific logic
def can_schedule_match_this_week(team, date, matches_played, max_matches_per_week):
    week_start = date - timedelta(days=date.weekday())
    week_end = week_start + timedelta(days=6)
    week_matches = matches_played[team].get((week_start, week_end), 0)
    if max_matches_per_week == 1 and week_matches >= 1:
        return False
    return True

# Main scheduling function
def schedule_matches(start_date, end_date, teams, teams_preferences, max_matches_per_week):
    schedule = []
    match_pairs = generate_round_robin(teams)
    ground_availability = {start_date + timedelta(days=x): time_slots[:] for x in range((end_date - start_date).days + 1)}
    ground_usage = {start_date + timedelta(days=x): {ground: 0 for ground in grounds} for x in range((end_date - start_date).days + 1)}

    # Track ground and day usage, matches, and last match date
    grounds_played = {team: {ground: 0 for ground in grounds} for team in teams}
    days_played = {team: {day: 0 for day in days_of_week} for team in teams}
    matches_played = {team: {} for team in teams}
    last_match_date = {team: None for team in teams}

    # Schedule each pair
    for pair in match_pairs:
        scheduled = False
        date = start_date

        while date <= end_date and not scheduled:
            day_name = date.strftime("%A")
            if (
                date.strftime("%Y-%m-%d") not in teams_preferences[pair[0]]["exceptions"]
                and date.strftime("%Y-%m-%d") not in teams_preferences[pair[1]]["exceptions"]
                and can_schedule_match_this_week(pair[0], date, matches_played, max_matches_per_week)
                and can_schedule_match_this_week(pair[1], date, matches_played, max_matches_per_week)
            ):
                # Determine the least-used day for both teams that is available
                if day_name in teams_preferences[pair[0]] and day_name in teams_preferences[pair[1]]:
                    team1_slots = teams_preferences[pair[0]].get(day_name, [])
                    team2_slots = teams_preferences[pair[1]].get(day_name, [])
                    available_slots = set(ground_availability[date]) & set(team1_slots) & set(team2_slots)

                    if available_slots:
                        slot = available_slots.pop()
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
                                "day": day_name,
                                "slot": slot
                            })

                            ground_availability[date].remove(slot)
                            week_start = date - timedelta(days=date.weekday())
                            matches_played[pair[0]][(week_start, week_start + timedelta(days=6))] = matches_played[pair[0]].get((week_start, week_start + timedelta(days=6)), 0) + 1
                            matches_played[pair[1]][(week_start, week_start + timedelta(days=6))] = matches_played[pair[1]].get((week_start, week_start + timedelta(days=6)), 0) + 1
                            days_played[pair[0]][day_name] += 1
                            days_played[pair[1]][day_name] += 1
                            scheduled = True
                            break
            date += timedelta(days=1)

        if not scheduled:
            schedule.append({
                "team1": pair[0],
                "team2": pair[1],
                "ground": "",
                "date": "",
                "day": "",
                "slot": ""
            })

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
    st.title("Cricket Tournament Scheduler")

    st.header("Tournament Setup")
    start_date = st.date_input("Select Tournament Start Date", datetime(2024, 8, 1))
    end_date = st.date_input("Select Tournament End Date", datetime(2024, 9, 30))

    num_teams = st.number_input("Number of teams", min_value=2, max_value=16, value=8, step=1)

    teams = []
    for i in range(num_teams):
        team_name = st.text_input(f"Enter name for Team {i+1}", f"Team {chr(65 + i)}")
        teams.append(team_name)

    max_matches_per_week = st.number_input("Maximum matches per week", min_value=1, max_value=2, value=2, step=1)

    st.header("Team Preferences")
    teams_preferences = {}

    for team in teams:
        st.subheader(f"{team}'s Preferences")
        team_pref = {}
        for day in days_of_week:
            slots = st.multiselect(f"Select slots for {team} on {day}", time_slots)
            team_pref[day] = slots

        exceptions = st.text_area(f"Enter exception dates for {team} (YYYY-MM-DD, comma-separated)", "")
        exception_days = [date.strip() for date in exceptions.split(",") if date.strip()]

        # Include days with selected slots only
        teams_preferences[team] = {day: team_pref[day] for day in days_of_week if team_pref[day]}
        teams_preferences[team]["exceptions"] = exception_days

    # Schedule and Reset Buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Generate Schedule"):
            st.write("Scheduling matches...")
            schedule = schedule_matches(start_date, end_date, teams, teams_preferences, max_matches_per_week)

            st.write("Match Schedule")
            for match in schedule:
                st.write(f"{match['team1']} vs {match['team2']} on {match['date']} ({match['day']}) at {match['ground']} during {match['slot']} slot")

            csv = create_csv(schedule)
            st.download_button(label="Download Schedule as CSV", data=csv, file_name="tournament_schedule.csv", mime="text/csv")
    
    with col2:
        if st.button("Reset"):
            st.experimental_rerun()

if __name__ == "__main__":
    main()
