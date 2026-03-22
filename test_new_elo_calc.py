import pandas as pd
import os

# --- 1. CONFIGURATION ---
INITIAL_ELO = 1500
K = 32
# Set this to True if you want to apply the 50% reset for a new season
APPLY_SEASON_REVERSION = False 

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

# --- 2. DATA LOADING ---
df = pd.read_csv('overwatch_results.csv')
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(by='Date')

ratings = {}
stats = {}
history = [] # To store every single rating change

def get_rating(team):
    # This is where we could load from starting_ratings_2017.csv if needed
    return ratings.get(team, INITIAL_ELO)

# --- 3. CALCULATION LOOP ---
for index, row in df.iterrows():
    t1_raw, t2_raw = str(row['TeamA']).strip(), str(row['TeamB']).strip()
    t1 = TEAM_NAMES.get(t1_raw, t1_raw)
    t2 = TEAM_NAMES.get(t2_raw, t2_raw)
    
    for t in [t1, t2]:
        if t not in stats:
            stats[t] = {'Wins': 0, 'Losses': 0, 'Played': 0}
            
    s1, s2 = row['ScoreA'], row['ScoreB']
    r1, r2 = get_rating(t1), get_rating(t2)
    
    # Elo Math
    exp1 = 1 / (1 + 10**((r2 - r1) / 400))
    actual1 = 1 if s1 > s2 else 0
    
    # Map Multiplier
    multiplier = (abs(s1 - s2) + 1) / 2
    shift = K * multiplier * (actual1 - exp1)
    
    # Update Ratings
    ratings[t1] = r1 + shift
    ratings[t2] = r2 - shift
    
    # Update Stats
    stats[t1]['Played'] += 1
    stats[t2]['Played'] += 1
    if s1 > s2:
        stats[t1]['Wins'] += 1
        stats[t2]['Losses'] += 1
    else:
        stats[t2]['Wins'] += 1
        stats[t1]['Losses'] += 1

    # RECORD HISTORY for time-traveling
    history.append({'Team': t1, 'Elo': ratings[t1], 'Date': row['Date']})
    history.append({'Team': t2, 'Elo': ratings[t2], 'Date': row['Date']})

# --- 4. MEAN REVERSION (Optional Season Reset) ---
if APPLY_SEASON_REVERSION:
    print("\n--- APPLYING SEASON RESET (50% Reversion) ---")
    for team in ratings:
        ratings[team] = ((ratings[team] - 1500) * 0.5) + 1500

# --- 5. FINAL LEADERBOARD GENERATION ---
leaderboard = pd.DataFrame([
    {'Team': team, 'Elo': ratings[team], 
     'W': stats[team]['Wins'], 'L': stats[team]['Losses'], 
     'GP': stats[team]['Played']} 
    for team in ratings
])
leaderboard['Elo'] = leaderboard['Elo'].round(2)
leaderboard = leaderboard.sort_values(by='Elo', ascending=False).reset_index(drop=True)
leaderboard.index += 1

# --- 6. INTERACTIVE FUNCTIONS ---
def show_rankings_on(date_str):
    try:
        target_date = pd.to_datetime(date_str)
        hist_df = pd.DataFrame(history)
        # Filter for the latest Elo of each team on or before that date
        on_date = (hist_df[hist_df['Date'] <= target_date]
                   .sort_values(by='Date', ascending=False)
                   .drop_duplicates('Team')
                   .sort_values(by='Elo', ascending=False))
        
        print(f"\n--- RANKINGS ON {target_date.date()} ---")
        if on_date.empty:
            print("No matches found before this date.")
        else:
            print(on_date[['Team', 'Elo']].reset_index(drop=True))
    except Exception as e:
        print(f"Invalid date format: {e}")

# --- 7. OUTPUT ---
print("\n--- FINAL OVERWATCH WORLD CUP RANKINGS ---")
print(leaderboard.to_string())

print(f"\nTotal System Elo: {leaderboard['Elo'].sum()}")
print(f"Expected Elo: {len(ratings) * 1500}")

# Ask user for time travel
while True:
    query = input("\nEnter a date (YYYY-MM-DD) to see historical rankings, or 'q' to quit: ")
    if query.lower() == 'q':
        break
    show_rankings_on(query)