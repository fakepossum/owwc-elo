import streamlit as st
import pandas as pd
import datetime

# 1. Page Configuration
st.set_page_config(page_title="OW World Cup Elo", page_icon="🏆", layout="wide")

# --- 2. CONSTANTS & MAPPINGS ---
BASE_ELO = 1500
K = 32
REVERSION_FACTOR = 0.5
HIATUS_REVERSION = 0.25

TEAM_NAMES = {
    'KSA': 'Saudi Arabia', 'FIN': 'Finland', 'KOR': 'South Korea',
    'CHN': 'China', 'USA': 'United States', 'GBR': 'United Kingdom',
    'CAN': 'Canada', 'COL': 'Colombia', 'AUS': 'Australia',
    'DNK': 'Denmark', 'NOR': 'Norway', 'JPN': 'Japan',
    'FRA': 'France', 'THA': 'Thailand', 'ESP': 'Spain'
}

# Web browsers support flags perfectly! No more [SA] needed.
FLAGS = {
    'Saudi Arabia': '🇸🇦', 'Finland': '🇫🇮', 'South Korea': '🇰🇷',
    'China': '🇨🇳', 'United States': '🇺🇸', 'United Kingdom': '🇬🇧',
    'Canada': '🇨🇦', 'Colombia': '🇨🇴', 'Australia': '🇦🇺',
    'Denmark': '🇩🇰', 'Norway': '🇳🇴', 'Japan': '🇯🇵',
    'France': '🇫🇷', 'Thailand': '🇹🇭', 'Spain': '🇪🇸'
}

def get_tier(elo):
    if elo >= 1700: return "🟢 Grandmaster"
    if elo >= 1600: return "🟣 Master"
    if elo >= 1500: return "🔵 Diamond"
    return "⚪ Platinum"

# --- 3. THE LOGIC (The math happens here) ---
@st.cache_data # This makes the dashboard fast by remembering the math
def calculate_elo():
    # RELATIVE PATH: Essential for Streamlit Cloud
    df = pd.read_csv('overwatch_results.csv', parse_dates=['Date'])
    df = df.sort_values('Date')
    
    ratings = {}
    stats = {}
    last_active = {}
    current_season_year = None
    
    for _, row in df.iterrows():
        match_year = row['Date'].year
        
        # Season Reset Logic
        if current_season_year is not None and match_year > current_season_year:
            reset = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
            for team in ratings:
                ratings[team] = ((ratings[team] - BASE_ELO) * reset) + BASE_ELO
        
        current_season_year = match_year
        
        # Match Processing
        t1_raw, t2_raw = str(row['TeamA']).strip(), str(row['TeamB']).strip()
        t1 = TEAM_NAMES.get(t1_raw, t1_raw)
        t2 = TEAM_NAMES.get(t2_raw, t2_raw)
        
        last_active[t1] = row['Date']
        last_active[t2] = row['Date']
        
        for t in [t1, t2]:
            if t not in ratings: ratings[t] = BASE_ELO
            if t not in stats: stats[t] = {'Wins': 0, 'Played': 0}
            
        r1, r2 = ratings[t1], ratings[t2]
        s1, s2 = row['ScoreA'], row['ScoreB']
        
        exp1 = 1 / (1 + 10**((r2 - r1) / 400))
        actual1 = 1 if s1 > s2 else (0.5 if s1 == s2 else 0)
        
        shift = K * ((abs(s1 - s2) + 1) / 2) * (actual1 - exp1)
        ratings[t1] += shift
        ratings[t2] -= shift
        
        stats[t1]['Played'] += 1
        stats[t2]['Played'] += 1
        if s1 > s2: stats[t1]['Wins'] += 1
        elif s2 > s1: stats[t2]['Wins'] += 1

    return ratings, stats, last_active, df['Date'].max()

# Execute math
ratings, stats, last_active, latest_date = calculate_elo()

# --- 4. THE WEB INTERFACE ---
st.title("🎮 OWWC: Live Elo Dashboard")

# Sidebar Filters
st.sidebar.header("Settings")
show_inactive = st.sidebar.checkbox("Show Teams Inactive > 2 Years", value=False)

# Build the Result Table
leaderboard = []
sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)

rank = 1
for team, elo in sorted_teams:
    days_since_active = (latest_date - last_active[team]).days
    is_active = days_since_active <= 730
    
    if show_inactive or is_active:
        flag = FLAGS.get(team, '🏳️')
        leaderboard.append({
            "Rank": rank,
            "Team": f"{flag} {team}",
            "Elo": round(elo, 1),
            "Tier": get_tier(elo),
            "Wins": stats[team]['Wins'],
            "Played": stats[team]['Played'],
            "Win Rate": f"{(stats[team]['Wins']/stats[team]['Played'])*100:.1f}%"
        })
        rank += 1

df_display = pd.DataFrame(leaderboard)

# Display Layout
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Global Power Rankings")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Podium")
    for i in range(min(3, len(df_display))):
        row = df_display.iloc[i]
        st.metric(label=f"Rank {row['Rank']}", value=row['Team'], delta=f"{row['Elo']} Elo")

st.caption(f"Data last updated based on match on: {latest_date.date()}")