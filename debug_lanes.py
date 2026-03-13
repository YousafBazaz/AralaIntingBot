"""Debug script to print all participants lanes and roles"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

RIOT_API_KEY = os.getenv('RIOT_API_KEY')
GAME_NAME = os.getenv('GAME_NAME', 'ArsyQuan')
TAG_LINE = os.getenv('TAG_LINE', 'EUW')

# Get user PUUID first
url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}'
headers = {'X-Riot-Token': RIOT_API_KEY}
response = requests.get(url, headers=headers)
puuid = response.json().get('puuid')

# Use the match ID from last_match_id.txt
with open('last_match_id.txt', 'r') as f:
    match_id = f.read().strip()

print(f"Checking match: {match_id}\n")

url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}'
headers = {'X-Riot-Token': RIOT_API_KEY}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    match_data = response.json()
    
    print("=" * 70)
    print("BLUE TEAM (teamId=100):")
    print("=" * 70)
    for p in match_data['info']['participants']:
        if p['teamId'] == 100:
            print(f"  {p['championName']:15} | Lane: {p.get('lane', 'Unknown'):10} | Role: {p.get('role', 'Unknown'):8} | Neutral CS: {p.get('neutralMinionsKilled', 0):3} | Lane CS: {p.get('totalMinionsKilled', 0):3}")
    
    print("\n" + "=" * 70)
    print("RED TEAM (teamId=200):")
    print("=" * 70)
    for p in match_data['info']['participants']:
        if p['teamId'] == 200:
            print(f"  {p['championName']:15} | Lane: {p.get('lane', 'Unknown'):10} | Role: {p.get('role', 'Unknown'):8} | Neutral CS: {p.get('neutralMinionsKilled', 0):3} | Lane CS: {p.get('totalMinionsKilled', 0):3}")
    
    print("\n" + "=" * 70)
    print("YOUR PLAYER INFO:")
    print("=" * 70)
    your_player = [p for p in match_data['info']['participants'] if p['puuid'] == puuid][0]
    print(f"  Champion: {your_player['championName']}")
    print(f"  API Lane: {your_player.get('lane', 'Unknown')}")
    print(f"  API Role: {your_player.get('role', 'Unknown')}")
    print(f"  Neutral Minions: {your_player.get('neutralMinionsKilled', 0)}")
    print(f"  Lane Minions: {your_player.get('totalMinionsKilled', 0)}")
else:
    print(f"API Error: {response.status_code}")
