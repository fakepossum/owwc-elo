import streamlit as st
import pandas as pd
import datetime

# 1. Page Configuration
st.set_page_config(page_title="OWWC Elo Dashboard", page_icon="🏆", layout="wide")

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
        
        if current_season_year is not None and match_year > current_season_year:
            reset = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
            for team in ratings:
                ratings[team] = ((ratings[team] - BASE_ELO) * reset) + BASE_ELO
                elo_history.append({"Date": match_date, "Team": team, "Elo": ratings[team]})
        
        current_season_year = match_year
        
        t1 = TEAM_NAMES.get(str(row['TeamA']).strip(), str(row['TeamA']).strip())
        t2 = TEAM_NAMES.get(str(row['TeamB']).strip(), str(row['TeamB']).strip())
        
        for t in [t1, t2]:
            if t not in ratings: 
                ratings[t] = BASE_ELO
                elo_history.append({"Date": match_date - datetime.timedelta(days=1), "Team": t, "Elo": BASE_ELO})
            if t not in stats: stats[t] = {'W': 0, 'L': 0, 'D': 0, 'GP': 0}
            
        s1, s2 = row['ScoreA'], row['ScoreB']
        r1, r2 = ratings[t1], ratings[t2]
        
        exp1 = 1 / (1 + 10**((r2 - r1) / 400))
        actual1 = 1 if s1 > s2 else (0.5 if s1 == s2 else