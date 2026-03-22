import pandas as pd
import math

# --- 1. CONFIGURATION ---
K = 32  
INITIAL_ELO = 1500

# Comprehensive Dictionary for all 2016 European Qualifier Teams
TEAM_NAMES = {
    # Europe, Middle East & Africa
    'IRL': 'Ireland', 'POL': 'Poland', 'ZAF': 'South Africa',
    'BCS': 'Baltic & Caspian', 'DEU': 'Germany', 'FIN': 'Finland',
    'HUN': 'Hungary', 'ISL': 'Iceland', 'GBR': 'United Kingdom', 'GRC': 'Greece',
    'HRV': 'Croatia', 'NOR': 'Norway', 'PRT': 'Portugal', 'FRA': 'France',
    'UKR': 'Ukraine', 'SVK': 'Slovakia', 'TUR': 'Turkey', 'ROU': 'Romania',
    'SWE': 'Sweden', 'DNK': 'Denmark','ITA': 'Italy', 'BGR': 'Bulgaria', 'RUS': 'Russia', 
    'CHE': 'Switzerland', 'ISR': 'Israel', 'AUT': 'Austria', 'SRB': 'Serbia', 
    'CZE': 'Czech Republic', 'BEN': 'Benelux', 'ESP': 'Spain',

    # Americas
    'USA': 'United States', 'CAN': 'Canada', 'MEX': 'Mexico', 'BRA': 'Brazil', 
    'ARG': 'Argentina', 'CHL': 'Chile', 'COL': 'Colombia', 'PER': 'Peru', 'VEN': 'Venezuela',
    'CRI': 'Costa Rica', 'ECU': 'Ecuador', 'URY': 'Uruguay', 'GUA': 'Guatemala', 
    'PAN': 'Panama', 'PAR': 'Paraguay', 'BOL': 'Bolivia', 'DOM': 'Dominican Republic', 
    'SLV': 'El Salvador',

    # Asia-Pacific
    'KOR': 'South Korea', 'JPN': 'Japan', 'CHN': 'China', 'AUS': 'Australia',
    'NZL': 'New Zealand', 'IND': 'India', 'SGP': 'Singapore', 'HKG': 'Hong Kong',
    'TWN': 'Taiwan', 'MYS': 'Malaysia', 'THA': 'Thailand', 'VNM': 'Vietnam',
    'PHL': 'Philippines', 'IDN': 'Indonesia', 'PAK': 'Pakistan', 'BGD': 'Bangladesh'}

# --- 2. LOAD & SORT DATA ---
# Ensure your CSV is named 'overwatch_results.csv'
df = pd.read_csv('overwatch_results.csv')

# Convert dates and sort chronologically
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(by='Date').reset_index(drop=True)

# --- 3. CALCULATION LOGIC ---
ratings = {}
stats = {}  # To track wins/losses and games played for each team

def get_rating(team):
    return ratings.get(team, INITIAL_ELO)

for index, row in df.iterrows():
    t1_raw, t2_raw = str(row['TeamA']).strip(), str(row['TeamB']).strip()
    t1 = TEAM_NAMES.get(t1_raw, t1_raw)
    t2 = TEAM_NAMES.get(t2_raw, t2_raw)

    # Initialize ratings and stats if teams are new
    for t in [t1, t2]:
        if t not in stats:
            stats[t] = {'Wins': 0, 'Losses': 0, 'Games Played': 0}
    
    s1, s2 = row['ScoreA'], row['ScoreB']
    r1, r2 = get_rating(t1), get_rating(t2)
    
    # Expected Score
    exp1 = 1 / (1 + 10**((r2 - r1) / 400))
    actual1 = 1 if s1 > s2 else 0
    
    # Track Win/Loss Stats
    stats[t1]['Games Played'] += 1
    stats[t2]['Games Played'] += 1
    if s1 > s2:
        stats[t1]['Wins'] += 1
        stats[t2]['Losses'] += 1
    else:
        stats[t1]['Losses'] += 1
        stats[t2]['Wins'] += 1
 
    # Map Differential Weighting
    map_diff = abs(s1 - s2)
    # Weighting: 2-1 = 1.0x, 2-0 = 1.5x, 3-0 = 2.0x
    multiplier = (map_diff + 1) / 2
    
    shift = K * multiplier * (actual1 - exp1)
    
    ratings[t1] = r1 + shift
    ratings[t2] = r2 - shift

# --- 4. DISPLAY RESULTS ---
leaderboard = pd.DataFrame([
    {'Team': team, 'Elo': ratings[team], 
     'W': stats[team]['Wins'], 'L': stats[team]['Losses'], 
     'GP': stats[team]['Games Played']} 
    for team in ratings
])

leaderboard['Elo'] = leaderboard['Elo'].round(2)
leaderboard = leaderboard.sort_values(by='Elo', ascending=False).reset_index(drop=True)
leaderboard.index += 1 

print("\n--- OVERWATCH WORLD CUP RANKINGS ---")
print(leaderboard.to_string())

# --- 5. VALIDATION & ACCURACY CHECKS ---
print(f"Total System Elo: {leaderboard['Elo'].sum()}")
print(f"Expected Elo: {len(ratings) * 1500}")

correct_predictions = 0
total_matches = 0

# Inside your loop...
if (r1 > r2 and s1 > s2) or (r2 > r1 and s2 > s1):
    correct_predictions += 1
total_matches += 1

# After the loop...
accuracy = (correct_predictions / total_matches) * 100
print(f"System Accuracy: {accuracy:.2f}%")