"""Debug script to check the current match lanes"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

RIOT_API_KEY = os.getenv('RIOT_API_KEY')

# Use the match ID from last_match_id.txt
with open('last_match_id.txt', 'r') as f:
    match_id = f.read().strip()

print(f"Checking match: {match_id}\n")

url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}'
headers = {'X-Riot-Token': RIOT_API_KEY}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    match_data = response.json()
    
    print("BLUE TEAM (teamId=100):")
    for p in match_data['info']['participants']:
        if p['teamId'] == 100:
            role = p.get('role', 'Unknown')
            print(f"  {p['championName']:15} - Lane: {p.get('lane', 'Unknown'):10} Role: {role}")
    
    print("\nRED TEAM (teamId=200):")
    for p in match_data['info']['participants']:
        if p['teamId'] == 200:
            role = p.get('role', 'Unknown')
            print(f"  {p['championName']:15} - Lane: {p.get('lane', 'Unknown'):10} Role: {role}")
else:
    print(f"API Error: {response.status_code}")
    print(response.text)
