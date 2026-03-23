import streamlit as st
import pandas as pd
import datetime
import altair as alt

# 1. Page Configuration
st.set_page_config(page_title="OWWC Elo Dashboard", page_icon="🏆", layout="wide")

# --- 2. CONSTANTS & MAPPINGS ---
BASE_ELO = 1500
K = 48
REVERSION_FACTOR = 0.8
HIATUS_REVERSION = 0.6

# Normalize 3-letter codes and common variations to full names
TEAM_NAMES = {
    'KSA': 'Saudi Arabia', 'KOR': 'South Korea', 'USA': 'United States',
    'CHN': 'China', 'FIN': 'Finland', 'GBR': 'United Kingdom',
    'CAN': 'Canada', 'FRA': 'France', 'JPN': 'Japan',
    'THA': 'Thailand', 'AUS': 'Australia', 'ESP': 'Spain',
    'COL': 'Colombia', 'DNK': 'Denmark', 'NOR': 'Norway',
    'RUS': 'Russia', 'SWE': 'Sweden', 'BRA': 'Brazil',
    'HKG': 'Hong Kong', 'ISL': 'Iceland', 'MEX': 'Mexico',
    'GTM': 'Guatemala', 'IND': 'India', 'LVA': 'Latvia',
    'PRY': 'Paraguay', 'PRI': 'Puerto Rico', 'ECU': 'Ecuador',
    'IRL': 'Ireland', 'POL': 'Poland', 'ZAF': 'South Africa',
    'BCS': 'Baltic & Caspian', 'DEU': 'Germany', 'FIN': 'Finland',
    'HUN': 'Hungary', 'ISL': 'Iceland', 'GBR': 'United Kingdom', 
    'GRC': 'Greece', 'HRV': 'Croatia', 'NOR': 'Norway', 
    'PRT': 'Portugal', 'FRA': 'France', 'UKR': 'Ukraine', 
    'SVK': 'Slovakia', 'TUR': 'Turkey', 'ROU': 'Romania',
    'SWE': 'Sweden', 'DNK': 'Denmark', 'ITA': 'Italy', 
    'BGR': 'Bulgaria', 'RUS': 'Russia', 'CHE': 'Switzerland',
    'ISR': 'Israel', 'AUT': 'Austria', 'SRB': 'Serbia', 
    'CZE': 'Czech Republic', 'BEN': 'Benelux', 'ESP': 'Spain',
    'USA': 'United States', 'CAN': 'Canada', 'BRA': 'Brazil', 
    'CHL': 'Chile', 'COL': 'Colombia', 'MEX': 'Mexico', 
    'ARG': 'Argentina', 'PER': 'Peru','KOR': 'South Korea', 'CHN': 'China', 'TWN': 'Taiwan', 
    'THA': 'Thailand', 'JPN': 'Japan', 'VNM': 'Vietnam', 
    'SGP': 'Singapore', 'HKG': 'Hong Kong', 'PHL': 'Philippines',
    'IDN': 'Indonesia', 'PAK': 'Pakistan', 'MYS': 'Malaysia','CRI': 'Costa Rica',
    'BEL': 'Belgium','NLD': 'Netherlands','NZL': 'New Zealand',
    'ROU': 'Romania','KSA': 'Saudi Arabia','PRY': 'Paraguay','IND': 'India',
    'LVA': 'Latvia','GTM': 'Guatemala','PRI': 'Puerto Rico','ECU': 'Ecuador',
    'HND': 'Honduras','SLV': 'El Salvador','URY': 'Uruguay','VEN': 'Venezuela'
}

FLAGS = {
    'Saudi Arabia': '🇸🇦', 'Finland': '🇫🇮', 'South Korea': '🇰🇷',
    'China': '🇨🇳', 'United States': '🇺🇸', 'United Kingdom': '🇬🇧',
    'Canada': '🇨🇦', 'Colombia': '🇨🇴', 'Australia': '🇦🇺',
    'Denmark': '🇩🇰', 'Norway': '🇳🇴', 'Japan': '🇯🇵',
    'France': '🇫🇷', 'Thailand': '🇹🇭', 'Spain': '🇪🇸',
    'Russia': '🇷🇺', 'Sweden': '🇸🇪', 'Brazil': '🇧🇷',
    'Hong Kong': '🇭🇰', 'Iceland': '🇮🇸', 'Mexico': '🇲🇽', 'Chile': '🇨🇱',
    'Colombia': '🇨🇴', 'Guatemala': '🇬🇹', 'India': '🇮🇳', 'Netherlands': '🇳🇱',
    'Paraguay': '🇵🇾', 'Puerto Rico': '🇵🇷', 'Ecuador': '🇪🇨', 'Belgium': '🇧🇪',
    'Germany': '🇩🇪', 'Italy': '🇮🇹', 'Switzerland': '🇨🇭', 'New Zealand': '🇳🇿',
    'Ireland': '🇮🇪', 'Poland': '🇵🇱', 'South Africa': '🇿🇦', 'Greece': '🇬🇷',
    'Croatia': '🇭🇷', 'Portugal': '🇵🇹', 'Ukraine': '🇺🇦','Czech Republic': '🇨🇿',
    'Austria': '🇦🇹', 'Serbia': '🇷🇸', 'Bulgaria': '🇧🇬','Hungary': '🇭🇺','Romania': '🇷🇴',
    'Vietnam': '🇻🇳', 'Singapore': '🇸🇬', 'Philippines': '🇵🇭', 'Indonesia': '🇮🇩',
    'Malaysia': '🇲🇾', 'Costa Rica': '🇨🇷', 'Benelux': '🇧🇪🇳🇱', 'Baltic & Caspian': '🌊',
    'Argentina': '🇦🇷', 'Peru': '🇵🇪','Turkey': '🇹🇷','Taiwan': '🇹🇼','Pakistan': '🇵🇰','Honduras': '🇭🇳',
    'Panama': '🇵🇦', 'Paraguay': '🇵🇾','Latvia': '🇱🇻','Slovenia': '🇸🇮','Slovakia': '🇸🇰','Serbia': '🇷🇸'
}

# --- 3. DATA PROCESSING ENGINE ---
@st.cache_data
def calculate_elo_data():
    df = pd.read_csv('overwatch_results.csv', parse_dates=['Date'])
    df = df.sort_values('Date')
    
    ratings = {}
    stats = {}
    last_active = {}
    team_form = {}
    elo_history = []
    current_season_year = None
    
    for _, row in df.iterrows():
        match_date = row['Date']
        match_year = match_date.year
        
        # 1. RAW DATA: Get names from the CSV and strip hidden spaces
        raw_a = str(row['TeamA']).strip()
        raw_b = str(row['TeamB']).strip()
        
        # 2. NORMALIZATION: Force everything to the "Full Name" version
        # We check the TEAM_NAMES map. If not found, we use the name as-is.
        t1 = TEAM_NAMES.get(raw_a, TEAM_NAMES.get(raw_a.upper(), raw_a))
        t2 = TEAM_NAMES.get(raw_b, TEAM_NAMES.get(raw_b.upper(), raw_b))

        # 3. SEASON RESET: (Must use the normalized 't1' and 't2' names)
        if current_season_year is not None and match_year > current_season_year:
            reset = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
            for team in ratings:
                ratings[team] = ((ratings[team] - BASE_ELO) * reset) + BASE_ELO
                elo_history.append({"Date": match_date, "Team": team, "Elo": ratings[team]})
        
        current_season_year = match_year
        
        # 4. INITIALIZE: Check for the normalized names in our dictionaries
        for t in [t1, t2]:
            if t not in ratings: 
                ratings[t] = BASE_ELO
                elo_history.append({"Date": match_date - datetime.timedelta(days=1), "Team": t, "Elo": BASE_ELO})
            if t not in stats: 
                stats[t] = {'W': 0, 'L': 0, 'D': 0, 'GP': 0}
            last_active[t] = match_date # Update activity tracker for the unified name
            if t not in team_form:
                team_form[t] = []
            
        # 5. MATH: Calculate using the unified names
        s1, s2 = row['ScoreA'], row['ScoreB']
        r1, r2 = ratings[t1], ratings[t2]
        
        # Elo Calculation
        exp1 = 1 / (1 + 10**((r2 - r1) / 400))
        actual1 = 1 if s1 > s2 else (0.5 if s1 == s2 else 0)
        shift = K * ((abs(s1 - s2) + 1) / 2) * (actual1 - exp1)
        
        ratings[t1] += shift
        ratings[t2] -= shift
        
        # Update Stats
        stats[t1]['GP'] += 1; stats[t2]['GP'] += 1
        if s1 > s2:
            stats[t1]['W'] += 1; stats[t2]['L'] += 1
        elif s2 > s1:
            stats[t2]['W'] += 1; stats[t1]['L'] += 1
        else:
            stats[t1]['D'] += 1; stats[t2]['D'] += 1

        # Update Team Form
        for t, score_self, score_opp in [(t1, s1, s2), (t2, s2, s1)]:
            if score_self > score_opp:
                res = "🟢" # Win
            elif score_self < score_opp:
                res = "🔴" # Loss
            else:
                res = "⚪" # Draw
            
            team_form[t].append(res)
            
            # Keep only the last 5 matches to keep the table clean
            if len(team_form[t]) > 5:
                team_form[t].pop(0)

        # Record History
        elo_history.append({"Date": match_date, "Team": t1, "Elo": ratings[t1]})
        elo_history.append({"Date": match_date, "Team": t2, "Elo": ratings[t2]})

    return ratings, stats, last_active, pd.DataFrame(elo_history), df['Date'].max(), team_form

# Run Calculation
ratings, stats, last_active, df_history, latest_date, team_form = calculate_elo_data()

# --- 4. SIDEBAR SETTINGS ---
st.sidebar.header("Dashboard Settings")
show_inactive = st.sidebar.checkbox("Show Inactive Teams", value=False, help="Show teams that haven't played in 2+ years")
all_teams = sorted(list(ratings.keys()))
selected_teams = st.sidebar.multiselect("Graph: Select Specific Teams", all_teams)

# --- 5. DATA PREPARATION ---
leaderboard = []
sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)

# --- 5.5 PREPARE YEARLY RANKINGS FOR GRAPH ---
# Create a copy of history and extract the year
df_ranks = df_history.copy()
df_ranks['Year'] = df_ranks['Date'].dt.year

# Get the last Elo entry for each team per year
df_yearly = df_ranks.groupby(['Year', 'Team'])['Elo'].last().reset_index()

# Calculate rank within each year (1 = highest Elo)
df_yearly['Rank'] = df_yearly.groupby('Year')['Elo'].rank(ascending=False, method='min')

# Optional: Filter for the graph
# (Same logic as before: Selected teams or Top 10)
display_teams = selected_teams if selected_teams else [t['RawName'] for t in leaderboard[:10]]
graph_rank_df = df_yearly[df_yearly['Team'].isin(display_teams)]

rank_counter = 1
for team, elo in sorted_teams:
    days_since_active = (latest_date - last_active[team]).days
    is_active = days_since_active <= 1460 # 4 years * 365 days
    form_string = "".join(team_form.get(team, []))
    
    if show_inactive or is_active:
        leaderboard.append({
            "Rank": rank_counter,
            "Team": f"{FLAGS.get(team, '🏳️')} {team}",
            "RawName": team,
            "ELO": round(float(elo), 1),
            "Form": form_string,
            "W": stats[team]['W'], "L": stats[team]['L'], 
            "D": stats[team]['D'], "GP": stats[team]['GP']
        })
        rank_counter += 1

df_leaderboard = pd.DataFrame(leaderboard)

# --- 5.6 CALCULATE TOP CLIMBERS (Active Teams Only) ---
years = sorted(df_yearly['Year'].unique())
top_5_climbers = []

if len(years) >= 2:
    current_yr = years[-1]
    previous_yr = years[-2]
    
    # 1. Filter df_yearly to only include teams currently considered "Active"
    # We pull the list of names from your already-filtered leaderboard
    active_team_names = [t['RawName'] for t in leaderboard]
    df_active_yearly = df_yearly[df_yearly['Team'].isin(active_team_names)].copy()
    
    # 2. RE-CALCULATE RANKS for those active teams only 
    # (This ensures Rank #1 in the table matches Rank #1 in the climber logic)
    df_active_yearly['ActiveRank'] = df_active_yearly.groupby('Year')['Elo'].rank(ascending=False, method='min')
    
    # 3. Get ranks for both years
    df_now = df_active_yearly[df_active_yearly['Year'] == current_yr][['Team', 'ActiveRank']]
    df_then = df_active_yearly[df_active_yearly['Year'] == previous_yr][['Team', 'ActiveRank']]
    
    # 4. Merge and calculate the jump
    df_climb = pd.merge(df_now, df_then, on='Team', suffixes=('_now', '_then'))
    df_climb['Jump'] = df_climb['ActiveRank_then'] - df_climb['ActiveRank_now']
    
    # 5. Sort by the biggest jump
    top_5_climbers = df_climb.sort_values(by='Jump', ascending=False).head(5).to_dict('records')

# --- 6. MAIN INTERFACE (TABS) ---
tab_rank, tab_predict, tab_graph = st.tabs(["🏆 Rankings", "⚔️ Match Predictor", "📈 Elo History"])

with tab_rank:
    col_main, col_metrics = st.columns([2, 1])
    
    with col_main:
        st.subheader("Global Leaderboard")
        st.dataframe(
            df_leaderboard,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ELO": st.column_config.NumberColumn("ELO", format="%.1f", width="auto"),
                "Team": st.column_config.TextColumn("Team", width="auto"),
                "Form": st.column_config.TextColumn("Last 5 Results", help="🟢=Win, 🔴=Loss, ⚪=Draw, latest match on the right",width="auto"),
                "RawName": None # Hide helper column
            }
        )
    
    with col_metrics:
        st.subheader("🚀 Top 5 Climbers")
        
        if top_5_climbers:
            for climber in top_5_climbers:
                t_name = climber['Team']
                t_flag = FLAGS.get(t_name, '🏳️')
                t_jump = int(climber['Jump'])
                t_rank_now = int(climber['ActiveRank_now'])
                
                st.metric(
                    label=f"{t_flag} Current Rank: #{t_rank_now}", 
                    value=t_name, 
                    delta=f"{t_jump} Spots",
                    delta_color="normal" # This enables Green for up, Red for down
                )
        else:
            st.info("Play more matches to see rank shifts!")

with tab_predict:
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

with tab_graph:
    st.subheader("Historical Rank Progression")
    
    # 1. Determine teams (Default to Top 10)
    display_teams = selected_teams if selected_teams else [t['RawName'] for t in leaderboard[:10]]
    graph_rank_df = df_yearly[df_yearly['Team'].isin(display_teams)]

    if not graph_rank_df.empty:
        # --- NEW: SELECTION LOGIC ---
        # This creates a click-to-highlight interaction
        selection = alt.selection_point(fields=['Team'], bind='legend')

        rank_chart = alt.Chart(graph_rank_df).mark_line(point=True, interpolate='monotone', strokeWidth=4).encode(
            x=alt.X('Year:O', title='Tournament Year'),
            y=alt.Y('Rank:Q', 
                    scale=alt.Scale(domain=[1, 20], reverse=True), 
                    title='World Ranking Position'),
            color=alt.Color('Team:N', title='Click Legend to Highlight'),
            # --- NEW: OPACITY LOGIC ---
            # If a team is selected, opacity is 1.0; otherwise, it's 0.1
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.1)),
            tooltip=['Year', 'Team', 'Rank', 'Elo']
        ).add_params(
            selection
        ).properties(
            height=500
        ).interactive()

        st.altair_chart(rank_chart, use_container_width=True)
        st.info("👆 **Tip:** Click a team name in the legend to highlight their specific path.")
    else:
        st.warning("No data found.")