"""Debug script to check ranked match history and champion win rate"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

RIOT_API_KEY = os.getenv('RIOT_API_KEY')
GAME_NAME = os.getenv('GAME_NAME', 'ArsyQuan')
TAG_LINE = os.getenv('TAG_LINE', 'EUW')
headers = {'X-Riot-Token': RIOT_API_KEY}

# Get PUUID
url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}'
puuid = requests.get(url, headers=headers).json().get('puuid')
print(f"PUUID: {puuid[:20]}...\n")

# Get last match to know which champion we're checking
with open('last_match_id.txt', 'r') as f:
    latest_match_id = f.read().strip()

latest_match = requests.get(f'https://europe.api.riotgames.com/lol/match/v5/matches/{latest_match_id}', headers=headers).json()
your_player = next(p for p in latest_match['info']['participants'] if p['puuid'] == puuid)
champion_name = your_player['championName']
queue_id_current = latest_match['info'].get('queueId', 'unknown')
is_ranked_current = queue_id_current in [420, 440]

print(f"Current match: {latest_match_id}")
print(f"Champion: {champion_name}")
print(f"Queue ID: {queue_id_current} ({'RANKED' if is_ranked_current else 'NOT RANKED - win rate will be seeded but this is not a ranked game!'})")
print(f"Result: {'WIN' if your_player['win'] else 'LOSS'}\n")

# Fetch ranked match IDs
all_match_ids = []
for queue_id, queue_name in [(420, 'Ranked Solo/Duo'), (440, 'Ranked Flex')]:
    url = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&start=0&count=20'
    ids = requests.get(url, headers=headers).json()
    print(f"{queue_name}: {len(ids)} matches found")
    for mid in ids[:5]:
        print(f"    {mid}")
    all_match_ids.extend(ids)

# Deduplicate
seen = set()
unique_ids = []
for m in all_match_ids:
    if m not in seen:
        seen.add(m)
        unique_ids.append(m)

print(f"\nTotal unique ranked matches: {len(unique_ids)}")
print(f"Is current match in history? {latest_match_id in unique_ids} (will be skipped to avoid double-counting)\n")

print(f"--- ALL {champion_name.upper()} MATCHES IN RANKED HISTORY (excluding current) ---")
wins = 0
total = 0
for match_id in unique_ids:
    if match_id == latest_match_id:
        continue  # skip current match, already seeded
    data = requests.get(f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}', headers=headers).json()
    for p in data.get('info', {}).get('participants', []):
        if p['puuid'] == puuid:
            if p.get('championName') == champion_name:
                result = "WIN" if p['win'] else "LOSS"
                total += 1
                if p['win']:
                    wins += 1
                print(f"  {match_id} → {result} ({p['kills']}/{p['deaths']}/{p['assists']})")
            break

print(f"\n--- SUMMARY ---")
print(f"From ranked history: {wins}W / {total - wins}L on {champion_name} in {total} games")
seed_win = 1 if your_player['win'] else 0
seed_loss = 0 if your_player['win'] else 1
print(f"Seeded with current: +{seed_win}W / +{seed_loss}L")
final_wins = wins + seed_win
final_losses = (total - wins) + seed_loss
final_total = total + 1
print(f"Bot will show: {final_wins}W / {final_losses}L ({round(final_wins/final_total*100)}%) in last {final_total} ranked games")
