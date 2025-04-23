import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import itertools
import random

def generate_schedule(teams, grounds, slots, start_date, max_matches_per_week, unavailable_slots, is_weekend_only, team_day_preferences, min_gap_days):
    schedule = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    match_combinations = list(itertools.combinations(teams, 2))
    max_date = start_date + timedelta(days=365)

    matches_scheduled_per_week = {team: {"week": 0, "count": 0} for team in teams}
    matches_scheduled_per_day = {team: set() for team in teams}
    last_match_date = {team: None for team in teams}
    slot_allocation = {}

    current_day = start_date

    while current_day <= max_date:
        day_name = days[current_day.weekday()]

        valid_day = (day_name in ["Saturday", "Sunday"]) if is_weekend_only else (day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        if not valid_day:
            current_day += timedelta(days=1)
            continue

        if current_day not in slot_allocation:
            slot_allocation[current_day] = {ground: set() for ground in grounds}

        unscheduled_matches = []
        matches_today = 0
        max_matches_today = len(teams) // 2

        for match in match_combinations:
            if matches_today >= max_matches_today:
                unscheduled_matches.append(match)
                continue

            team1, team2 = match
            scheduled = False

            current_week = (current_day - start_date).days // 7 + 1

            # Check team constraints
            if matches_scheduled_per_week[team1]["week"] == current_week and matches_scheduled_per_week[team1]["count"] >= max_matches_per_week:
                unscheduled_matches.append(match)
                continue
            if matches_scheduled_per_week[team2]["week"] == current_week and matches_scheduled_per_week[team2]["count"] >= max_matches_per_week:
                unscheduled_matches.append(match)
                continue

            if current_day in matches_scheduled_per_day[team1] or current_day in matches_scheduled_per_day[team2]:
                unscheduled_matches.append(match)
                continue

            # Check minimum gap
            if last_match_date[team1] and (current_day - last_match_date[team1]).days < min_gap_days:
                unscheduled_matches.append(match)
                continue
            if last_match_date[team2] and (current_day - last_match_date[team2]).days < min_gap_days:
                unscheduled_matches.append(match)
                continue

            # Check day preferences (full match condition)
            if day_name not in team_day_preferences[team1] and day_name not in team_day_preferences[team2]:
                unscheduled_matches.append(match)
                continue

            # If shared preference not found, fallback to single-team preference
            if day_name not in team_day_preferences[team1] and day_name not in team_day_preferences[team2]:
                unscheduled_matches.append(match)
                continue

            available_slots = [(ground, slot) for ground in grounds for slot in slots]
            random.shuffle(available_slots)

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
                last_match_date[team1] = current_day
                last_match_date[team2] = current_day
                slot_allocation[current_day][ground].add(slot)

                scheduled = True
                matches_today += 1
                break

            if not scheduled:
                unscheduled_matches.append(match)

        match_combinations = unscheduled_matches
        current_day += timedelta(days=1)

        if not match_combinations:
            break

    # Schedule remaining matches with relaxed conditions
    for match in match_combinations:
        team1, team2 = match
        fallback_day = None
        for day in team_day_preferences[team1].union(team_day_preferences[team2]):
            fallback_day = day
            break

        fallback_date = start_date
        while fallback_date <= max_date:
            day_name = fallback_date.strftime('%A')
            if day_name == fallback_day:
                available_slots = [(ground, slot) for ground in grounds for slot in slots]
                random.shuffle(available_slots)

                for ground, slot in available_slots:
                    if (fallback_date, ground, slot) in unavailable_slots:
                        continue

                    schedule.append({
                        "Team1": team1,
                        "Team2": team2,
                        "Date": fallback_date.strftime('%Y-%m-%d'),
                        "Day": day_name,
                        "Ground": ground,
                        "Slot": slot
                    })
                    break
                break
            fallback_date += timedelta(days=1)

    return schedule

# UI Section
st.set_page_config(layout="wide")
st.title("🏏 One7 Cricket Tournament Scheduler")
st.markdown("Design fair and efficient match schedules with smart constraints and preferences.")

with st.expander("Tournament Settings", expanded=True):
    tournament_name = st.text_input("🏷️ Tournament Name", "My Tournament")
    num_teams = st.number_input("🔢 Number of Teams", min_value=2, step=1)
    team_names = [st.text_input(f"Team {i+1} Name", key=f"team_{i}") for i in range(num_teams)]

    create_pools = st.checkbox("🔀 Create Pools?")
    if create_pools:
        num_pools = st.number_input("Number of Pools", min_value=1, step=1)
        pools = {f"Pool {i+1}": [] for i in range(num_pools)}
        for i, team in enumerate(team_names):
            pool_name = f"Pool {(i % num_pools) + 1}"
            pools[pool_name].append(team)
    else:
        pools = {"Pool 1": team_names}

with st.expander("Grounds and Time Slots"):
    base_grounds = ["Off Stump", "Middle Stump", "Leg Stump", "Yug-1", "Yug-2"]
    custom_grounds = st.text_area("Additional Grounds (comma-separated)")
    if custom_grounds:
        base_grounds.extend([g.strip() for g in custom_grounds.split(",")])
    selected_grounds = st.multiselect("🏟️ Select Grounds", base_grounds, default=base_grounds)

    slots = ["Morning", "Afternoon", "Evening", "Night"]
    selected_slots = st.multiselect("🕓 Select Available Slots", slots, default=slots)

with st.expander("Match Preferences & Constraints"):
    start_date = st.date_input("📅 Tournament Start Date", datetime.today())
    weekend_only = st.radio("🗓️ Tournament Type", ("Weekend Only", "Weekdays Only")) == "Weekend Only"
    max_matches_per_week = st.number_input("⚖️ Max Matches Per Team Per Week", min_value=1, step=1)
    min_gap_days = 1 if max_matches_per_week == 1 else 3
    st.markdown(f"⏳ **Minimum Days Gap Between Matches:** {min_gap_days} day(s)")

with st.expander("Team-Specific Day Preferences"):
    day_options = ["Saturday", "Sunday"] if weekend_only else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    team_day_preferences = {}
    for team in team_names:
        team_days = st.multiselect(f"🗓️ Preferred Days for {team}", day_options, default=day_options, key=f"{team}_dayprefs")
        team_day_preferences[team] = set(team_days)

with st.expander("Unavailable Slot Management"):
    unavailable_slots = set()
    for ground in selected_grounds:
        st.write(f"📍 Mark Unavailable Slots for {ground}")
        unavailable_dates = st.multiselect(f"Unavailable Dates for {ground}", [
            (start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(0, 180)
        ], key=f"{ground}_dates")
        for date_str in unavailable_dates:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            unavailable_times = st.multiselect(f"Unavailable Slots on {date} at {ground}", slots, key=f"{ground}_{date}_slots")
            for slot in unavailable_times:
                unavailable_slots.add((date, ground, slot))

# Generate Schedule Button
if st.button("🚀 Generate Match Schedule"):
    all_schedules = []

    for pool_name, pool_teams in pools.items():
        schedule = generate_schedule(
            pool_teams,
            selected_grounds,
            selected_slots,
            start_date,
            max_matches_per_week,
            unavailable_slots,
            weekend_only,
            team_day_preferences,
            min_gap_days
        )
        for match in schedule:
            match["Pool"] = pool_name
        all_schedules.extend(schedule)

    schedule_df = pd.DataFrame(all_schedules)
    st.success("✅ Schedule Generated!")
    st.dataframe(schedule_df)

    csv = schedule_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Schedule as CSV",
        data=csv,
        file_name=f"{tournament_name}_schedule.csv",
        mime="text/csv"
    )
