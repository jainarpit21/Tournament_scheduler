import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import itertools
import random

# Helper functions
def generate_schedule(teams, grounds, slots, start_date, max_matches_per_week, unavailable_slots, is_weekend_only):
    schedule = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    match_combinations = list(itertools.combinations(teams, 2))
    max_date = start_date + timedelta(days=365)  # Limit scheduling to within one year
    matches_scheduled_per_week = {team: {"week": 0, "count": 0} for team in teams}
    matches_scheduled_per_day = {team: set() for team in teams}  # Track daily matches to avoid multiple matches per day
    slot_allocation = {}  # Track slot allocation for each ground per day

    st.write("Starting schedule generation...")
    st.write(f"Teams: {teams}")
    st.write(f"Grounds: {grounds}")
    st.write(f"Slots: {slots}")
    st.write(f"Start Date: {start_date}")
    st.write(f"Unavailable Slots: {unavailable_slots}")

    current_day = start_date

    while current_day <= max_date:
        day_name = days[current_day.weekday()]

        # Skip non-weekend days if it's a weekend-only tournament
        if is_weekend_only and day_name not in ["Saturday", "Sunday"]:
            current_day += timedelta(days=1)
            continue

        # Reset slot allocation for the current day
        if current_day not in slot_allocation:
            slot_allocation[current_day] = {ground: set() for ground in grounds}

        unscheduled_matches = []

        for match in match_combinations:
            scheduled = False
            team1, team2 = match

            # Check weekly and daily constraints
            current_week = (current_day - start_date).days // 7 + 1
            if matches_scheduled_per_week[team1]["week"] == current_week and matches_scheduled_per_week[team1]["count"] >= max_matches_per_week:
                unscheduled_matches.append(match)
                continue
            if matches_scheduled_per_week[team2]["week"] == current_week and matches_scheduled_per_week[team2]["count"] >= max_matches_per_week:
                unscheduled_matches.append(match)
                continue
            if current_day in matches_scheduled_per_day[team1] or current_day in matches_scheduled_per_day[team2]:
                unscheduled_matches.append(match)
                continue

            available_slots = [(ground, slot) for ground in grounds for slot in slots]
            random.shuffle(available_slots)  # Randomize slot and ground allocation

            for ground, slot in available_slots:
                if (current_day, ground, slot) in unavailable_slots or slot in slot_allocation[current_day][ground]:
                    continue

                # Schedule the match
                schedule.append({
                    "Team1": team1,
                    "Team2": team2,
                    "Date": current_day.strftime('%Y-%m-%d'),
                    "Day": day_name,
                    "Ground": ground,
                    "Slot": slot
                })

                # Update tracking variables
                if matches_scheduled_per_week[team1]["week"] != current_week:
                    matches_scheduled_per_week[team1]["week"] = current_week
                    matches_scheduled_per_week[team1]["count"] = 0

                if matches_scheduled_per_week[team2]["week"] != current_week:
                    matches_scheduled_per_week[team2]["week"] = current_week
                    matches_scheduled_per_week[team2]["count"] = 0

                matches_scheduled_per_week[team1]["count"] += 1
                matches_scheduled_per_week[team2]["count"] += 1

                matches_scheduled_per_day[team1].add(current_day)
                matches_scheduled_per_day[team2].add(current_day)

                slot_allocation[current_day][ground].add(slot)

                scheduled = True
                break

            if not scheduled:
                unscheduled_matches.append(match)

        # Move to the next day and retry unscheduled matches
        match_combinations = unscheduled_matches
        current_day += timedelta(days=1)

        # Stop if no matches remain
        if not match_combinations:
            break

    # Add unscheduled matches
    for match in match_combinations:
        schedule.append({
            "Team1": match[0],
            "Team2": match[1],
            "Date": "",
            "Day": "",
            "Ground": "",
            "Slot": ""
        })

    return schedule

# Streamlit UI
st.title("Cricket Tournament Scheduler")
st.subheader("Create a customizable round-robin tournament schedule")

tournament_name = st.text_input("Enter the tournament name:", "My Tournament")

num_teams = st.number_input("Enter the number of teams:", min_value=2, step=1)
team_names = [st.text_input(f"Enter name for Team {i+1}:") for i in range(num_teams)]

create_pools = st.checkbox("Do you want to create separate pools?")

if create_pools:
    num_pools = st.number_input("Enter the number of pools:", min_value=1, step=1)
    pools = {f"Pool {i+1}": [] for i in range(num_pools)}

    for i, team in enumerate(team_names):
        pool_name = f"Pool {(i % num_pools) + 1}"
        pools[pool_name].append(team)
else:
    pools = {"Pool 1": team_names}

available_grounds = ["Off Stump", "Middle Stump", "Leg Stump", "Yug-1", "Yug-2"]
custom_grounds = st.text_area("Enter additional grounds (comma-separated):")
if custom_grounds:
    available_grounds.extend([ground.strip() for ground in custom_grounds.split(",")])

selected_grounds = st.multiselect("Select the grounds for the tournament:", available_grounds, default=available_grounds)

start_date = st.date_input("Select the tournament starting date:", datetime.today())
slots = ["Morning", "Afternoon", "Evening", "Night"]
selected_slots = st.multiselect("Select available slots:", slots, default=slots)

weekend_only = st.radio("Is this a weekend-only tournament?", ("Yes", "No")) == "Yes"
max_matches_per_week = st.number_input("Maximum matches per team per week:", min_value=1, step=1)

# Unavailable slots selection
st.subheader("Mark unavailable slots")
unavailable_slots = set()

for ground in selected_grounds:
    st.write(f"Mark unavailable slots for {ground}")
    unavailable_dates = st.multiselect(f"Select multiple unavailable dates for {ground}", [
        (start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(0, 365)
    ], key=f"{ground}_dates")

    for date_str in unavailable_dates:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        unavailable_times = st.multiselect(f"Select slots unavailable on {date} for {ground}", slots, key=f"{ground}_{date}_slots")

        for slot in unavailable_times:
            unavailable_slots.add((date, ground, slot))

# Generate Schedule
if st.button("Generate Schedule"):
    all_schedules = []

    for pool_name, pool_teams in pools.items():
        schedule = generate_schedule(
            pool_teams,
            selected_grounds,
            selected_slots,
            start_date,
            max_matches_per_week,
            unavailable_slots,
            weekend_only
        )
        for match in schedule:
            match["Pool"] = pool_name
        all_schedules.extend(schedule)

    schedule_df = pd.DataFrame(all_schedules)

    st.dataframe(schedule_df)
    csv = schedule_df.to_csv(index=False)
    st.download_button(
        label="Download Schedule as CSV",
        data=csv,
        file_name=f"{tournament_name}_schedule.csv",
        mime="text/csv"
    )
