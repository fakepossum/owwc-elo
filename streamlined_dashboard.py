import streamlit as st
import pandas as pd
import datetime
import altair as alt
import json

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# Tip for the future: Move these dictionaries to a separate 'config.json' file.
# ==========================================
BASE_ELO = 1500
K = 32
REVERSION_FACTOR = 0.85
HIATUS_REVERSION = 0.7

with open('config.json', 'r', encoding='utf-8') as file:
    config_data = json.load(file)

TEAM_NAMES = config_data['TEAM_NAMES']
FLAGS = config_data['FLAGS']
REGIONS = config_data['REGIONS']

TEAM_TO_REGION = {team: region for region, teams in REGIONS.items() for team in teams}

# ==========================================
# 2. BACKEND ENGINE (Logic & Data)
# ==========================================
@st.cache_data
def calculate_elo_data():
    df = pd.read_csv('overwatch_results.csv', parse_dates=['Date'])
    df = df.sort_values('Date')
    
    ratings, stats, last_active, team_form = {}, {}, {}, {}
    elo_history = []
    current_season_year = None
    
    for _, row in df.iterrows():
        match_date = row['Date']
        match_year = match_date.year
        
        raw_a = str(row['TeamA']).strip()
        raw_b = str(row['TeamB']).strip()
        
        t1 = TEAM_NAMES.get(raw_a, TEAM_NAMES.get(raw_a.upper(), raw_a))
        t2 = TEAM_NAMES.get(raw_b, TEAM_NAMES.get(raw_b.upper(), raw_b))

        if current_season_year is not None and match_year > current_season_year:
            reset = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
            for team in ratings:
                ratings[team] = ((ratings[team] - BASE_ELO) * reset) + BASE_ELO
                elo_history.append({"Date": match_date, "Team": team, "Elo": ratings[team]})
        
        current_season_year = match_year
        
        for t in [t1, t2]:
            if t not in ratings: 
                ratings[t] = BASE_ELO
                elo_history.append({"Date": match_date - datetime.timedelta(days=1), "Team": t, "Elo": BASE_ELO})
            if t not in stats: 
                stats[t] = {'W': 0, 'L': 0, 'D': 0, 'GP': 0}
            last_active[t] = match_date 
            if t not in team_form:
                team_form[t] = []
            
        s1, s2 = row['ScoreA'], row['ScoreB']
        r1, r2 = ratings[t1], ratings[t2]
        
        exp1 = 1 / (1 + 10**((r2 - r1) / 400))
        actual1 = 1 if s1 > s2 else (0.5 if s1 == s2 else 0)
        shift = K * ((abs(s1 - s2) + 1) / 2) * (actual1 - exp1)
        
        ratings[t1] += shift
        ratings[t2] -= shift
        
        stats[t1]['GP'] += 1; stats[t2]['GP'] += 1
        if s1 > s2:
            stats[t1]['W'] += 1; stats[t2]['L'] += 1
        elif s2 > s1:
            stats[t2]['W'] += 1; stats[t1]['L'] += 1
        else:
            stats[t1]['D'] += 1; stats[t2]['D'] += 1

        for t, score_self, score_opp in [(t1, s1, s2), (t2, s2, s1)]:
            res = "🟢" if score_self > score_opp else ("🔴" if score_self < score_opp else "⚪")
            team_form[t].append(res)
            if len(team_form[t]) > 5:
                team_form[t].pop(0)

        elo_history.append({"Date": match_date, "Team": t1, "Elo": ratings[t1]})
        elo_history.append({"Date": match_date, "Team": t2, "Elo": ratings[t2]})

    return df, ratings, stats, last_active, pd.DataFrame(elo_history), df['Date'].max(), team_form


def prepare_dashboard_data(ratings, stats, last_active, df_history, latest_date, team_form, show_inactive, selected_region):
    """Processes raw backend data into structured dataframes for the UI."""
    leaderboard = []
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)

    # Yearly rankings
    df_ranks = df_history.copy()
    df_ranks['Year'] = df_ranks['Date'].dt.year
    df_yearly = df_ranks.groupby(['Year', 'Team'])['Elo'].last().reset_index()
    df_yearly['Rank'] = df_yearly.groupby('Year')['Elo'].rank(ascending=False, method='min')

    # Leaderboard generation
    rank_counter = 1
    for team, elo in sorted_teams:
        days_since_active = (latest_date - last_active[team]).days
        is_active = days_since_active <= 1460 
        form_string = "".join(team_form.get(team, []))
        
        if show_inactive or is_active:
            leaderboard.append({
                "Rank": rank_counter,
                "Team": f"{FLAGS.get(team, '🏳️')} {team}",
                "RawName": team,
                "ELO": round(float(elo), 1),
                "Region": TEAM_TO_REGION.get(team, 'Unknown'),
                "Form": form_string,
                "W": stats[team]['W'], "L": stats[team]['L'], 
                "D": stats[team]['D'], "GP": stats[team]['GP']
            })
            rank_counter += 1

    df_leaderboard = pd.DataFrame(leaderboard)
    df_leaderboard['Region'] = df_leaderboard['RawName'].map(TEAM_TO_REGION).fillna('Unknown')
    df_filtered = df_leaderboard[df_leaderboard['Region'].isin(selected_region)]

    # Top Climbers
    years = sorted(df_yearly['Year'].unique())
    top_5_climbers = []

    if len(years) >= 2:
        current_yr, previous_yr = years[-1], years[-2]
        active_team_names = [t['RawName'] for t in leaderboard]
        df_active_yearly = df_yearly[df_yearly['Team'].isin(active_team_names)].copy()
        
        df_active_yearly['ActiveRank'] = df_active_yearly.groupby('Year')['Elo'].rank(ascending=False, method='min')
        df_now = df_active_yearly[df_active_yearly['Year'] == current_yr][['Team', 'ActiveRank']]
        df_then = df_active_yearly[df_active_yearly['Year'] == previous_yr][['Team', 'ActiveRank']]
        
        df_climb = pd.merge(df_now, df_then, on='Team', suffixes=('_now', '_then'))
        df_climb['Jump'] = df_climb['ActiveRank_then'] - df_climb['ActiveRank_now']
        top_5_climbers = df_climb.sort_values(by='Jump', ascending=False).head(5).to_dict('records')

    return df_filtered, df_yearly, top_5_climbers


# ==========================================
# 3. FRONTEND UI COMPONENTS
# ==========================================
def render_sidebar(all_teams):
    st.sidebar.header("Dashboard Settings")
    show_inactive = st.sidebar.checkbox("Show Inactive Teams", value=False, help="Show teams that haven't played in 2+ years")
    regions_list = ['Americas', 'EMEA', 'APAC']
    selected_region = st.sidebar.multiselect("Filter by Region", options=regions_list, default=regions_list)
    selected_teams = st.sidebar.multiselect("Graph: Select Specific Teams", all_teams)
    
    return show_inactive, selected_region, selected_teams


def render_rankings_tab(df_filtered, top_5_climbers):
    col_main, col_metrics = st.columns([2, 1])
    
    with col_main:
        st.subheader("Global Leaderboard")
        st.dataframe(
            df_filtered,
            use_container_width=True, hide_index=True, height=700,
            column_config={
                "ELO": st.column_config.NumberColumn("ELO", format="%.1f", width="auto"),
                "Team": st.column_config.TextColumn("Team", width="auto"),
                "Region": st.column_config.TextColumn("Region", width="auto"),
                "Form": st.column_config.TextColumn("Last 5 Results", help="🟢=Win, 🔴=Loss, ⚪=Draw, latest match on the right",width="auto"),
                "RawName": None 
            }
        )
    
    with col_metrics:
        st.subheader("🚀 Top 5 Climbers")
        if top_5_climbers:
            for climber in top_5_climbers:
                st.metric(
                    label=f"{FLAGS.get(climber['Team'], '🏳️')} Current Rank: #{int(climber['ActiveRank_now'])}", 
                    value=climber['Team'], 
                    delta=f"{int(climber['Jump'])} Spots",
                    delta_color="normal"
                )
        else:
            st.info("Play more matches to see rank shifts!")


def render_predictor_tab(ratings, all_teams):
    st.subheader("Win Probability Calculator")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        t1 = st.selectbox("Team 1", all_teams, index=0, key="p1")
    with pcol2:
        t2 = st.selectbox("Team 2", all_teams, index=1, key="p2")
    
    if t1 and t2:
        r1, r2 = ratings[t1], ratings[t2]
        prob1 = 1 / (1 + 10**((r2 - r1) / 400))
        st.divider()
        st.markdown(f"### {FLAGS.get(t1, '🏳️')} {t1} vs {FLAGS.get(t2, '🏳️')} {t2}")
        m1, m2 = st.columns(2)
        m1.metric(f"{t1} Chance", f"{prob1:.1%}")
        m2.metric(f"{t2} Chance", f"{(1-prob1):.1%}")
        st.progress(prob1)


def render_graph_tab(df_yearly, df_filtered, selected_teams):
    st.subheader("Historical Rank Progression")
    
    current_list = df_filtered.to_dict('records')
    display_teams = selected_teams if selected_teams else [t['RawName'] for t in current_list[:10]]
    graph_rank_df = df_yearly[df_yearly['Team'].isin(display_teams)]

    if not graph_rank_df.empty:
        selection = alt.selection_point(fields=['Team'], bind='legend')

        rank_chart = alt.Chart(graph_rank_df).mark_line(point=True, interpolate='monotone', strokeWidth=4).encode(
            x=alt.X('Year:O', title='Tournament Year'),
            y=alt.Y('Rank:Q', scale=alt.Scale(domain=[1, 20], reverse=True), title='World Ranking Position'),
            color=alt.Color('Team:N', title='Click Legend to Highlight'),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.1)),
            tooltip=['Year', 'Team', 'Rank', 'Elo']
        ).add_params(selection).properties(height=500).interactive()

        st.altair_chart(rank_chart, use_container_width=True)
        st.info("👆 **Tip:** Click a team name in the legend to highlight their specific path.")
    else:
        st.warning("No data found.")


# ==========================================
# 4. MAIN EXECUTION BLOCK
# ==========================================
def main():
    # Page Config must be the first Streamlit command
    st.set_page_config(page_title="OWWC Elo Dashboard", page_icon="🏆", layout="wide")

    # 1. Fetch Backend Data
    df, ratings, stats, last_active, df_history, latest_date, team_form = calculate_elo_data()
    all_teams = sorted(list(ratings.keys()))

    # 2. Render Sidebar
    show_inactive, selected_region, selected_teams = render_sidebar(all_teams)

    # 3. Process Data for UI
    df_filtered, df_yearly, top_5_climbers = prepare_dashboard_data(
        ratings, stats, last_active, df_history, latest_date, team_form, show_inactive, selected_region
    )

    # 4. Render Main Interface
    tab_rank, tab_predict, tab_graph, tab_recent = st.tabs(["🏆 Rankings", "⚔️ Match Predictor", "📈 Elo History", "📅 Recent & Upcoming"])
    
    with tab_rank:
        render_rankings_tab(df_filtered, top_5_climbers)
    with tab_predict:
        render_predictor_tab(ratings, all_teams)
    with tab_graph:
        render_graph_tab(df_yearly, df_filtered, selected_teams)
    with tab_recent:
        # --- 1. COUNTDOWN SECTION (Centered) ---
        count_spacer_l, count_content, count_spacer_r = st.columns([1, 2, 1])
        
        with count_content:
            st.subheader("🚀 Next Qualifiers Countdown")
            target_date = datetime.datetime(2026, 4, 17, 17, 0, 0, tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            time_diff = target_date - now

            if time_diff.total_seconds() > 0:
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Days", days)
                c2.metric("Hours", hours)
                c3.metric("Minutes", minutes)
                c4.metric("Seconds", seconds)
            else:
                st.success("🎉 The Qualifiers are LIVE!")
        
        st.divider()

        # --- 2. RECENT RESULTS SECTION (Narrower for Readability) ---
        st.subheader("📝 Latest Match Results")
        
        spacer_left, table_body, spacer_right = st.columns([1, 3, 1])

        with table_body:
            # 1. Prepare the data
            recent_matches = df.sort_values('Date', ascending=False).head(15).copy()
            
            # Clean names and flags
            recent_matches['TeamA'] = recent_matches['TeamA'].apply(lambda x: f"{FLAGS.get(TEAM_NAMES.get(x.strip(), x.strip()), '🏳️')} {TEAM_NAMES.get(x.strip(), x.strip())}")
            recent_matches['TeamB'] = recent_matches['TeamB'].apply(lambda x: f"{FLAGS.get(TEAM_NAMES.get(x.strip(), x.strip()), '🏳️')} {TEAM_NAMES.get(x.strip(), x.strip())}")
            
            # 2. Define the Highlighting Function
            def highlight_winner(row):
                # Default styles (no background)
                style_a = ''
                style_b = ''
                
                if row['ScoreA'] > row['ScoreB']:
                    style_a = 'background-color: rgba(0, 255, 0, 0.2); font-weight: bold;' # Light Green
                elif row['ScoreB'] > row['ScoreA']:
                    style_b = 'background-color: rgba(0, 255, 0, 0.2); font-weight: bold;' # Light Green
                    
                return [None, style_a, None, None, style_b] # Mapping styles to columns: Date, TeamA, ScoreA, ScoreB, TeamB

            # 3. Apply Styling and Display
            # We select only the columns we want to display before styling
            display_df = recent_matches[['Date', 'TeamA', 'ScoreA', 'ScoreB', 'TeamB']]
            
            # Apply the style row-by-row
            styled_df = display_df.style.apply(highlight_winner, axis=1)

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "TeamA": st.column_config.TextColumn("Home Team"),
                    "TeamB": st.column_config.TextColumn("Away Team"),
                    "ScoreA": st.column_config.NumberColumn(" ", width="small"),
                    "ScoreB": st.column_config.NumberColumn(" ", width="small")
                }
            )

# Start the application
if __name__ == "__main__":
    main()