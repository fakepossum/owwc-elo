from tabulate import tabulate
from colorama import Fore, Style, init
import datetime
import pandas as pd
import os

init(autoreset=True)

# --- 1. CONFIGURATION ---
INITIAL_ELO = 1500
K = 32
BASE_ELO = 1500
REVERSION_FACTOR = 0.5

# Legacy Mapping: Handles 2016 teams splitting or rebranding in 2017
LEGACY_MAPPING = {
    'Belgium': 'Benelux',
    'Netherlands': 'Benelux',
    'Estonia': 'Baltic & Caspian',
    'Latvia': 'Baltic & Caspian',
    'Lithuania': 'Baltic & Caspian'
}

TEAM_NAMES = {
    # 2016 Teams
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
    'CRI': 'Costa Rica',
    # 2017 Specific New Codes/Names
    'BEL': 'Belgium',
    'NLD': 'Netherlands',
    'NZL': 'New Zealand',
    'ROU': 'Romania',
    # 2019 New Competitors
    'KSA': 'Saudi Arabia',
    'PRY': 'Paraguay',
    'IND': 'India',
    'LVA': 'Latvia',
    'GTM': 'Guatemala',
    'PRI': 'Puerto Rico',
    'ECU': 'Ecuador',
}

# Map codes to Names + Flags for the visual output
FLAGS = {
    'South Korea': '🇰🇷', 'Finland': '🇫🇮', 'Saudi Arabia': '🇸🇦', 
    'China': '🇨🇳', 'United States': '🇺🇸', 'Canada': '🇨🇦', 
    'Denmark': '🇩🇰', 'United Kingdom': '🇬🇧', 'Netherlands': '🇳🇱'
}

def get_tier(elo):
    if elo >= 1700: return f"{Fore.CYAN}Grandmaster"
    if elo >= 1600: return f"{Fore.MAGENTA}Master"
    if elo >= 1500: return f"{Fore.BLUE}Diamond"
    return f"{Fore.WHITE}Platinum"

# --- 2. DATA LOADING ---
if not os.path.exists('overwatch_results.csv'):
    print("Error: 'overwatch_results.csv' not found.")
    exit()

df = pd.read_csv('overwatch_results.csv')
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(by='Date')

ratings = {}
stats = {}
history = [] 
last_active = {}
current_season_year = None

# --- 3. CALCULATION LOOP ---
for index, row in df.iterrows():
    match_year = row['Date'].year
    
    # --- SEASON TRANSITION LOGIC ---
    if current_season_year is not None and match_year > current_season_year:
        print(f"\n>>> 🎆 New Year Detected: {match_year}. Applying Reset & Legacy Mapping...")
        
        # Save snapshot of pre-reset ratings for inheritance logic
        old_year_final = ratings.copy()
        
        # Apply 50% Mean Reversion to all existing teams
        for team in ratings:
            ratings[team] = ((ratings[team] - BASE_ELO) * REVERSION_FACTOR) + BASE_ELO
            
        # Apply Legacy Inheritance (Splits and Renames)
        for new_team, old_team in LEGACY_MAPPING.items():
            if old_team in old_year_final and new_team not in ratings:
                # Calculate what the inherited score should be (after reversion)
                inherited_score = ((old_year_final[old_team] - BASE_ELO) * REVERSION_FACTOR) + BASE_ELO
                ratings[new_team] = inherited_score
                stats[new_team] = {'Wins': 0, 'Losses': 0, 'Played': 0}
                print(f"    {new_team} inherited {inherited_score:.2f} from {old_team}")

    current_season_year = match_year

    # --- MATCH PROCESSING ---
    t1_raw, t2_raw = str(row['TeamA']).strip(), str(row['TeamB']).strip()
    t1 = TEAM_NAMES.get(t1_raw, t1_raw)
    t2 = TEAM_NAMES.get(t2_raw, t2_raw)

    # Track activity for potential inactivity handling
    last_active[t1] = row['Date']
    last_active[t2] = row['Date']
    
    for t in [t1, t2]:
        if t not in ratings:
            ratings[t] = INITIAL_ELO
        if t not in stats:
            stats[t] = {'Wins': 0, 'Losses': 0, 'Played': 0}
            
    s1, s2 = row['ScoreA'], row['ScoreB']
    r1, r2 = ratings[t1], ratings[t2]
    
    # Elo Math
    exp1 = 1 / (1 + 10**((r2 - r1) / 400))
    # Refined Win/Loss/Draw Logic
    if s1 > s2:
        actual1 = 1
    elif s1 < s2:
        actual1 = 0
    else:
        actual1 = 0.5  # This handles the 2-2 draws
    
    multiplier = (abs(s1 - s2) + 1) / 2
    shift = K * multiplier * (actual1 - exp1)
    
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

    # Record History
    history.append({'Team': t1, 'Elo': ratings[t1], 'Date': row['Date']})
    history.append({'Team': t2, 'Elo': ratings[t2], 'Date': row['Date']})

# --- 4. LEADERBOARD GENERATION (With Filtering) ---
# We use the latest date in your data as the "Current Day"
system_today = df['Date'].max() 

filtered_data = []
for team in ratings:
    # Calculate how long it's been since their last match
    last_seen = last_active.get(team)
    if last_seen:
        days_since_played = (system_today - last_seen).days
        
        # Change 1460 to any number of days you want (1460 = 4 years)
        if days_since_played <= 1460:  # Only include teams active within the last 4 years
            filtered_data.append({
                'Team': team, 
                'Elo': ratings[team], 
                'W': stats[team]['Wins'], 
                'L': stats[team]['Losses'], 
                'GP': stats[team]['Played'],
                'Last Match': last_seen.date()
            })

leaderboard = pd.DataFrame(filtered_data)
leaderboard['Elo'] = leaderboard['Elo'].round(2)
leaderboard = leaderboard.sort_values(by='Elo', ascending=False).reset_index(drop=True)
leaderboard.index += 1

# --- 5. INTERACTIVE FUNCTIONS ---
def show_rankings_on(date_str):
    try:
        target_date = pd.to_datetime(date_str)
        hist_df = pd.DataFrame(history)
        on_date = (hist_df[hist_df['Date'] <= target_date]
                   .sort_values(by='Date', ascending=False)
                   .drop_duplicates('Team')
                   .sort_values(by='Elo', ascending=False))
        
        print(f"\n--- RANKINGS ON {target_date.date()} ---")
        if on_date.empty:
            print("No matches found before this date.")
        else:
            print(on_date[['Team', 'Elo']].reset_index(drop=True))
    except:
        print("Invalid date format. Use YYYY-MM-DD.")

# --- 6. OUTPUT ---
def print_final_rankings(ratings, stats, last_active):
    latest_date = max(last_active.values())
    table_data = []
    
    # Sort by Elo
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    
    rank = 1
    for team, elo in sorted_teams:
        last_seen = last_active.get(team)
        # Hide teams inactive for more than 2 years (730 days)
        if (latest_date - last_seen).days <= 730:
            flag = FLAGS.get(team, '🏳️')
            table_data.append([
                rank, f"{flag} {team}", f"{elo:.2f}", 
                get_tier(elo), stats[team]['Wins'], stats[team]['Losses']
            ])
            rank += 1

    headers = ["#", "Team", "Elo", "Tier", "W", "L"]
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}🏆 ACTIVE OVERWATCH WORLD CUP RANKINGS 🏆")
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))

# Call this at the very end of your script:

print_final_rankings(ratings, stats, last_active)


while True:
    query = input("\nEnter date (YYYY-MM-DD) for historical rankings, or 'q' to quit: ")
    if query.lower() == 'q':
        break
    show_rankings_on(query)