import sys
try:
    from tabulate import tabulate
    from colorama import Fore, Style, init
    import pandas as pd
    print("✅ Libraries loaded successfully!")
except ImportError as e:
    print(f"❌ Library missing: {e}")
    print("Run: pip install tabulate colorama pandas")
    sys.exit()

# Initialize colorama
init(autoreset=True)

# 1. Test Data (Simulating your Elo results)
test_data = [
    {"Rank": "🥇", "Team": "🇸🇦 Saudi Arabia", "Elo": 1745.71, "Tier": f"{Fore.CYAN}Grandmaster"},
    {"Rank": "🥈", "Team": "🇫🇮 Finland", "Elo": 1698.42, "Tier": f"{Fore.MAGENTA}Master"},
    {"Rank": "🥉", "Team": "🇰🇷 South Korea", "Elo": 1693.58, "Tier": f"{Fore.MAGENTA}Master"},
    {"Rank": 4, "Team": "🇨🇳 China", "Elo": 1681.86, "Tier": f"{Fore.MAGENTA}Master"},
    {"Rank": 5, "Team": "🇺🇸 USA", "Elo": 1649.02, "Tier": f"{Fore.MAGENTA}Master"}
]

df_test = pd.DataFrame(test_data)

# 2. Test Visual Output
print(f"\n{Fore.YELLOW}{Style.BRIGHT}--- ELO VISUAL TERMINAL TEST ---")

# We use 'fancy_grid' to test if your terminal supports the professional borders
print(tabulate(df_test, headers='keys', tablefmt='fancy_grid', showindex=False))

print(f"\n{Fore.GREEN}Test Complete!")
print(f"{Fore.WHITE}If the table borders look straight and the flags appear, your system is 100% ready.")