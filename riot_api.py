import os
import time
import requests

GAME_NAME = os.getenv('GAME_NAME', 'ArsyQuan')
TAG_LINE = os.getenv('TAG_LINE', 'EUW')
REGION = os.getenv('REGION', 'euw1')

def get_puuid():
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')  # <-- Move inside the function
    url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}'
    headers = {'X-Riot-Token': RIOT_API_KEY}
    response = requests.get(url, headers=headers)
    print("Account API response:", response.json())
    return response.json().get('puuid')

def get_latest_match_id(puuid):
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')  # <-- Move inside the function
    match_url = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1'
    headers = {'X-Riot-Token': RIOT_API_KEY}
    response = requests.get(match_url, headers=headers)
    matches = response.json()
    print("Match API response:", matches)
    if isinstance(matches, list) and matches:
        return matches[0]
    else:
        return None

def get_match_stats(puuid, match_id):
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')  # <-- Move inside the function
    match_url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': RIOT_API_KEY}
    response = requests.get(match_url, headers=headers)
    match_data = response.json()
    print("Match details response:", match_data)

    player_team_id = None
    player_stats = None
    team_kills = 0
    
    # Get match end timestamp (in milliseconds)
    end_timestamp = match_data.get('info', {}).get('gameEndTimestamp')
    if not end_timestamp:
        # If not present, estimate using start + duration
        start_timestamp = match_data.get('info', {}).get('gameStartTimestamp', 0)
        duration = match_data.get('info', {}).get('gameDuration', 0)
        end_timestamp = start_timestamp + (duration * 1000)

    # Convert to seconds
    end_time = end_timestamp / 1000
    now = time.time()
    seconds_ago = int(now - end_time)
    # Format as "X hours/minutes ago"
    if seconds_ago < 60:
        time_ago = f"{seconds_ago} seconds ago"
    elif seconds_ago < 3600:
        minutes = seconds_ago // 60
        time_ago = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = seconds_ago // 3600
        time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"

    for participant in match_data.get('info', {}).get('participants', []):
        if participant['puuid'] == puuid:
            player_team_id = participant['teamId']
            player_stats = participant
            break

    if not player_stats:
        return None, None, None, None, None, None, None, None, None, None

    for participant in match_data.get('info', {}).get('participants', []):
        if participant['teamId'] == player_team_id:
            team_kills += participant['kills']

    k = player_stats['kills']
    d = player_stats['deaths']
    a = player_stats['assists']
    kda = f"{k}/{d}/{a}"
    score = player_stats.get('champLevel', 'N/A')
    damage = player_stats.get('totalDamageDealtToChampions', 'N/A')
    champ = player_stats.get('championName', 'Unknown')
    totalMinionsKilled = player_stats.get('totalMinionsKilled', 'N/A')
    victory = "Victory" if player_stats.get('win', False) else "Defeat"
    time_dead = player_stats.get('totalTimeSpentDead', 'N/A')

    kill_participation = 0
    if team_kills > 0:
        kill_participation = round(((k + a) / team_kills) * 100, 1)
    else:
        kill_participation = 0
    
    game_mode = match_data.get('info', {}).get('gameMode', 'Unknown')
    #role = player_stats.get('teamPosition', player_stats.get('role', 'Unknown'))
    #if not role or role.upper() == "NONE":
        #role = "N/A"
    lane = player_stats.get('lane', 'Unknown')



    return kda, score, damage, champ, totalMinionsKilled, victory, time_dead, kill_participation, game_mode, lane, time_ago