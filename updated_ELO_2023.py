import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init
import datetime

# Initialize colors for Windows Terminal
init(autoreset=True)

# --- 1. CONFIGURATION & CONSTANTS ---
BASE_ELO = 1500
INITIAL_ELO = 1500
K = 32
REVERSION_FACTOR = 0.5  # Standard 50% year-over-year reset
HIATUS_REVERSION = 0.25 # Heavier 75% reset for the 2019 -> 2023 gap

# Map 3-letter CSV codes to Full Names
TEAM_NAMES = {
    'KSA': 'Saudi Arabia', 'FIN': 'Finland', 'KOR': 'South Korea',
    'CHN': 'China', 'USA': 'United States', 'GBR': 'United Kingdom',
    'CAN': 'Canada', 'COL': 'Colombia', 'AUS': 'Australia',
    'DNK': 'Denmark', 'NOR': 'Norway', 'JPN': 'Japan',
    'RUS': 'Russia', 'ESP': 'Spain', 'FRA': 'France', 'THA': 'Thailand'
}

# Meta-data for Visuals: (Emoji, 3-Letter Code)
# This acts as a fail-safe if the Flag Emoji doesn't render on Windows
TEAM_META = {
    'Saudi Arabia': ('[SA]', 'KSA'),
    'Finland': ('[FI]', 'FIN'),
    'South Korea': ('[KR]', 'KOR'),
    'China': ('[CN]', 'CHN'),
    'United States': ('[US]', 'USA'),
    'United Kingdom': ('[GB]', 'GBR'),
    'Canada': ('[CA]', 'CAN'),
    'Colombia': ('[CO]', 'COL'),
    'Australia': ('[AU]', 'AUS'),
    'Denmark': ('[DK]', 'DNK'),
    'Norway': ('[NO]', 'NOR'),
    'Japan': ('[JP]', 'JPN'),
    'Spain': ('[ES]', 'ESP'),
    'France': ('[FR]', 'FRA'),
    'Thailand': ('[TH]', 'THA')
}

# Teams that inherited scores from defunct regions
LEGACY_MAPPING = {
    'Belgium': 'Benelux',
    'Netherlands': 'Benelux',
    'Estonia': 'Baltic & Caspian',
    'Latvia': 'Baltic & Caspian',
    'Lithuania': 'Baltic & Caspian'
}

# --- 2. HELPER FUNCTIONS ---
def get_tier(elo):
    if elo >= 1700: return f"{Fore.LIGHTCYAN_EX}GM"
    if elo >= 1600: return f"{Fore.LIGHTMAGENTA_EX}MS"
    if elo >= 1500: return f"{Fore.LIGHTBLUE_EX}DM"
    return f"{Fore.WHITE}PT"

# --- 3. DATA INITIALIZATION ---
df = pd.read_csv('overwatch_results.csv', parse_dates=['Date'])
df = df.sort_values('Date')

ratings = {}
stats = {}
last_active = {}
current_season_year = None

# --- 4. CALCULATION LOOP ---
for index, row in df.iterrows():
    match_year = row['Date'].year
    
    # --- SEASON TRANSITION & MEAN REVERSION ---
    if current_season_year is not None and match_year > current_season_year:
        print(f"\n>>> 🎆 New Year Detected: {match_year}. Applying Reset...")
        
        # Determine reset strength (Normal vs Pandemic Hiatus)
        reset_strength = HIATUS_REVERSION if (current_season_year == 2019 and match_year == 2023) else REVERSION_FACTOR
        
        old_ratings = ratings.copy()
        for team in ratings:
            ratings[team] = ((ratings[team] - BASE_ELO) * reset_strength) + BASE_ELO
            
        # Handle Legacy Inheritance
        for new_team, old_team in LEGACY_MAPPING.items():
            if old_team in old_ratings and new_team not in ratings:
                inherited = ((old_ratings[old_team] - BASE_ELO) * reset_strength) + BASE_ELO
                ratings[new_team] = inherited
                stats[new_team] = {'Wins': 0, 'Losses': 0, 'Played': 0}

    current_season_year = match_year

    # --- MATCH PROCESSING ---
    t1_raw, t2_raw = str(row['TeamA']).strip(), str(row['TeamB']).strip()
    t1 = TEAM_NAMES.get(t1_raw, t1_raw)
    t2 = TEAM_NAMES.get(t2_raw, t2_raw)
    
    # Update Last Active Date
    last_active[t1] = row['Date']
    last_active[t2] = row['Date']
    
    for t in [t1, t2]:
        if t not in ratings: ratings[t] = INITIAL_ELO
        if t not in stats: stats[t] = {'Wins': 0, 'Losses': 0, 'Played': 0}
            
    s1, s2 = row['ScoreA'], row['ScoreB']
    r1, r2 = ratings[t1], ratings[t2]
    
    # Elo Math
    exp1 = 1 / (1 + 10**((r2 - r1) / 400))
    if s1 > s2: actual1 = 1
    elif s1 < s2: actual1 = 0
    else: actual1 = 0.5 
    
    multiplier = (abs(s1 - s2) + 1) / 2
    shift = K * multiplier * (actual1 - exp1)
    
    ratings[t1] += shift
    ratings[t2] -= shift
    
    # Update Record
    stats[t1]['Played'] += 1
    stats[t2]['Played'] += 1
    if s1 > s2:
        stats[t1]['Wins'] += 1
        stats[t2]['Losses'] += 1
    elif s2 > s1:
        stats[t2]['Wins'] += 1
        stats[t1]['Losses'] += 1

# --- 5. FINAL OUTPUT GENERATION ---
def print_final_leaderboard():
    latest_match_date = df['Date'].max()
    table_data = []
    
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    
    rank = 1
    for team, elo in sorted_teams:
        last_seen = last_active.get(team)
        if last_seen and (latest_match_date - last_seen).days <= 730:
            # We fetch the bracketed code [SA] instead of the emoji for alignment
            flag_icon, code = TEAM_META.get(team, ('[--]', team[:3].upper()))
            
            # Tier formatting
            tier_display = get_tier(elo)
            
            table_data.append([
                f"{Fore.YELLOW}{rank}" if rank <= 3 else rank, 
                f"{flag_icon} {team}", 
                f"{elo:.1f}", 
                tier_display, 
                stats[team]['Wins'], 
                stats[team]['Played'],
                last_seen.strftime('%Y-%m')
            ])
            rank += 1

    headers = ["#", "Team", "Elo", "Tier", "W", "GP", "Active"]
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}█║ OVERWATCH WORLD CUP GLOBAL RANKINGS ║█")
    # Using 'simple' or 'github' table format prevents the zig-zag alignment issues
    print(tabulate(table_data, headers=headers, tablefmt="simple")) 
    print(f"\n{Style.DIM}Sorted by Elo • Inactivity Filter: 2 Years")

print_final_leaderboard()