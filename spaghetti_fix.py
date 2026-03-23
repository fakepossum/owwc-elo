import csv
import os
import re
import pandas as pd

# --- 1. PASTE YOUR MESSY TEXT BELOW ---
# You can paste dates, scores, and teams in a "staircase" format here.
raw_mess = """
March 14, 2026

IND
0
2

PHL

SGP
0
2

NZL

PAK
2
1

PHL

IND
2
0

MYS

IND
2
0

SGP

MYS
0
2

PHL

MYS
0
2

SGP

NZL
1
2

PAK

March 15, 2026

NZL
1
2

IND

PAK
2
1

SGP

NZL
1
2

PHL

IND
2
0

PAK

PHL
2
0

SGP

NZL
2
1

MYS

MYS
0
2

PAK
""" 
# ---------------------------------------

# --- 2. TEAM NAME DICTIONARY ---
# This ensures "ESP" becomes "Spain" etc. in your CSV.
TEAM_NAMES = {
    # Europe, Middle East & Africa
    'IRL': 'Ireland', 'POL': 'Poland', 'ZAF': 'South Africa',
    'BCS': 'Baltic & Caspian', 'DEU': 'Germany', 'FIN': 'Finland',
    'HUN': 'Hungary', 'ISL': 'Iceland', 'GBR': 'United Kingdom', 'GRC': 'Greece',
    'HRV': 'Croatia', 'NOR': 'Norway', 'PRT': 'Portugal', 'FRA': 'France',
    'UKR': 'Ukraine', 'SVK': 'Slovakia', 'TUR': 'Turkey', 'ROU': 'Romania',
    'SWE': 'Sweden', 'DNK': 'Denmark','ITA': 'Italy', 'BGR': 'Bulgaria', 'RUS': 'Russia', 
    'CHE': 'Switzerland', 'ISR': 'Israel', 'AUT': 'Austria', 'SRB': 'Serbia', 
    'CZE': 'Czech Republic', 'BEN': 'Benelux', 'ESP': 'Spain', 'NLD': 'Netherlands', 'BEL': 'Belgium',

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

def clean_spaghetti(text):
    print("--- Overwatch Smart Data Importer ---")
    # Fallback if no date is found in the text block
    default_date = input("Enter fallback date for matches without a header (YYYY-MM-DD): ")
    current_date = default_date
    
    # Filter out empty lines
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    matches = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if line is a Date (e.g., October 29, 2016)
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        date_match = re.search(date_pattern, line, re.IGNORECASE)
        
        if date_match:
            try:
                # Convert "October 29, 2016" to "2016-10-29"
                current_date = pd.to_datetime(date_match.group()).strftime('%Y-%m-%d')
                print(f"📅 Date context switched to: {current_date}")
            except Exception as e:
                print(f"⚠️ Could not parse date '{line}', using previous date.")
            i += 1
            continue
        
        # Check if we have enough lines left for a match block (Team, Score, Score, Team)
        if i + 3 < len(lines):
            # Validation: Are the middle two lines numbers?
            if lines[i+1].replace('.', '', 1).isdigit() and lines[i+2].replace('.', '', 1).isdigit():
                t_a_raw = lines[i]
                s_a = lines[i+1]
                s_b = lines[i+2]
                t_b_raw = lines[i+3]
                
                # Apply dictionary translation
                t_a = TEAM_NAMES.get(t_a_raw, t_a_raw)
                t_b = TEAM_NAMES.get(t_b_raw, t_b_raw)
                
                matches.append([current_date, t_a, t_b, s_a, s_b])
                i += 4 # Skip ahead 4 lines to the next potential block
            else:
                # Not a match block or a date, move to next line
                i += 1
        else:
            break

    # --- SAVE TO CSV ---
    file_path = 'overwatch_results.csv'
    file_exists = os.path.isfile(file_path)

    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Add headers only if file is new or empty
        if not file_exists or os.stat(file_path).st_size == 0:
            writer.writerow(["Date", "TeamA", "TeamB", "ScoreA", "ScoreB"])
        
        writer.writerows(matches)
    
    print(f"\n✅ Success! {len(matches)} matches processed and added to '{file_path}'.")

if __name__ == "__main__":
    clean_spaghetti(raw_mess)