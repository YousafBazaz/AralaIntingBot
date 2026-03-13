"""Debug script to check all available ward/vision related fields"""
import os
from dotenv import load_dotenv
import requests
import json

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
    
    # Get your player stats
    players = match_data['info']['participants']
    your_player = [p for p in players if p['puuid'] == puuid][0]
    champ = your_player['championName']
    
    print(f"YOUR STATS ({champ}):\n")
    
    # Check all ward/vision related fields
    vision_fields = {
        'visionScore': 'Vision Score',
        'wardsPlaced': 'Wards Placed (yellow)',
        'wardsKilled': 'Wards Destroyed',
        'detectorWardsPlaced': 'Control Wards Placed (pink)',
    }
    
    for field, label in vision_fields.items():
        value = your_player.get(field, 'NOT AVAILABLE')
        print(f"{label}: {value}")
    
else:
    print(f"API Error: {response.status_code}")
