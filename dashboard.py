import streamlit as st
import pandas as pd
import datetime

# 1. Page Configuration
st.set_page_config(page_title="OWWC ELO Dashboard", page_icon="🏆", layout="wide")

# --- 2. CONSTANTS & MAPPINGS ---
BASE_ELO = 1500
K = 32
REVERSION_FACTOR = 0.5
HIATUS_REVERSION = 0.25

TEAM_NAMES = {
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
    'ARG': 'Argentina', 'PER': 'Peru',
    'KOR': 'South Korea', 'CHN': 'China', 'TWN': 'Taiwan', 
    'THA': 'Thailand', 'JPN': 'Japan', 'VNM': 'Vietnam', 
    'SGP': 'Singapore', 'HKG': 'Hong Kong', 'PHL': 'Philippines',
    'IDN': 'Indonesia', 'PAK': 'Pakistan', 'MYS': 'Malaysia',
    'CRI': 'Costa Rica', 'BEL': 'Belgium','NLD': 'Netherlands', 'NZL': 'New Zealand',
    'ROU': 'Romania','KSA': 'Saudi Arabia','PRY': 'Paraguay','IND': 'India','LVA': 'Latvia',
    'GTM': 'Guatemala','PRI': 'Puerto Rico','ECU': 'Ecuador'
}

FLAGS = {
    'Saudi Arabia': '🇸🇦', 'Finland': '🇫🇮', 'South Korea': '🇰🇷',
    'China': '🇨🇳', 'United States': '🇺🇸', 'United Kingdom': '🇬🇧',
    'Canada': '🇨🇦', 'Colombia': '🇨🇴', 'Australia': '🇦🇺',
    'Denmark': '🇩🇰', 'Norway': '🇳🇴', 'Japan': '🇯🇵',
    'France': '🇫🇷', 'Thailand': '🇹🇭', 'Spain': '🇪🇸'
}

# --- 3. THE LOGIC (Math + History Tracking) ---
@st.cache_data
def calculate_elo_data():
    # Relative path for Streamlit Cloud
    df = pd.read_csv('overwatch_results.csv', parse_dates=['Date'])
    df = df.sort_values('Date')
    
    ratings = {}
    stats = {}
    elo_history = []
    current_season_year = None
    
    for _, row in df.iterrows():
        match_date = row['Date']
        match_year = match_date.year
        
        # --- STEP 1: NORMALIZE IMMEDIATELY ---
        # This forces 'KOR', 'kor', and 'South Korea' to all become 'South Korea'
        raw_a = str(row['TeamA']).strip()
        raw_b = str(row['TeamB']).strip()
        
        # We check the mapping; if not found, we use the name as provided
        t1 = TEAM_NAMES.get(raw_a, TEAM_NAMES.get(raw_a.upper(), raw_a))
        t2 = TEAM_NAMES.get(raw_b, TEAM_NAMES.get(raw_b.upper(), raw_b))

        # --- STEP 2: SEASON RESET ---
        # Now that names are normalized, the reset applies to the "unified" team
        if current_season_year is not None and match_year > current_season_year:
            reset = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
            for team in ratings:
                ratings[team] = ((ratings[team] - BASE_ELO) * reset) + BASE_ELO
                elo_history.append({"Date": match_date, "Team": team, "ELO": ratings[team]})
        
        current_season_year = match_year
        
        # --- STEP 3: INITIALIZE RATINGS ---
        for t in [t1, t2]:
            if t not in ratings: 
                ratings[t] = BASE_ELO
                # Record starting point for the graph
                elo_history.append({"Date": match_date - datetime.timedelta(days=1), "Team": t, "ELO": BASE_ELO})
            if t not in stats: 
                stats[t] = {'W': 0, 'L': 0, 'D': 0, 'GP': 0}
            
        # --- STEP 4: CALCULATION ---
        s1, s2 = row['ScoreA'], row['ScoreB']
        r1, r2 = ratings[t1], ratings[t2]
        
        # ... rest of your ELO math ...
        
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

        elo_history.append({"Date": match_date, "Team": t1, "ELO": ratings[t1]})
        elo_history.append({"Date": match_date, "Team": t2, "ELO": ratings[t2]})

    return ratings, stats, pd.DataFrame(elo_history), df['Date'].max()

ratings, stats, df_history, latest_date = calculate_elo_data()

# --- 4. WEB INTERFACE ---
st.title("🎮 OWWC: Global ELO Dashboard")

# --- SIDEBAR: MATCH CALCULATOR ---
st.sidebar.header("⚔️ Match Predictor")
team_a_sel = st.sidebar.selectbox("Team 1", sorted(ratings.keys()), index=0)
team_b_sel = st.sidebar.selectbox("Team 2", sorted(ratings.keys()), index=1)

if team_a_sel and team_b_sel:
    r1, r2 = ratings[team_a_sel], ratings[team_b_sel]
    win_prob_a = 1 / (1 + 10**((r2 - r1) / 400))
    win_prob_b = 1 - win_prob_a
    
    st.sidebar.write(f"**{team_a_sel}**: {win_prob_a:.1%}")
    st.sidebar.progress(win_prob_a)
    st.sidebar.write(f"**{team_b_sel}**: {win_prob_b:.1%}")
    st.sidebar.divider()

st.sidebar.header("⚙️ Settings")
all_teams = sorted(list(ratings.keys()))
selected_teams = st.sidebar.multiselect("Graph Teams", all_teams, default=['South Korea', 'China', 'Saudi Arabia'])

# --- MAIN LAYOUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Leaderboard")
    leaderboard = []
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    
    for rank, (team, elo) in enumerate(sorted_teams, 1):
        leaderboard.append({
            "Rank": rank,
            "Team": f"{FLAGS.get(team, '🏳️')} {team}",
            "ELO": round(elo, 1),
            "W": stats[team]['W'], "L": stats[team]['L'], "D": stats[team]['D'], "GP": stats[team]['GP']
        })
    st.dataframe(pd.DataFrame(leaderboard), use_container_width=True, hide_index=True)

with col2:
    st.subheader("Top 10 Nations")
    for i in range(min(10, len(leaderboard))):
        st.metric(label=f"Rank {leaderboard[i]['Rank']}", value=leaderboard[i]['Team'], delta=f"{leaderboard[i]['ELO']} ELO")

# --- 5. PROGRESSION GRAPH ---
st.divider()
st.subheader("📈 ELO Progression")
if selected_teams:
    graph_df = df_history[df_history['Team'].isin(selected_teams)]
    st.line_chart(graph_df, x="Date", y="ELO", color="Team", use_container_width=True)

st.caption(f"Last updated: {latest_date.date()} | Predicted win chance based on current ELO gap.")