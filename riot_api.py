import os
import time
import requests
import random


def correct_lane_from_cs(api_lane, neutral_cs, lane_cs, role):
    """
    Correct lane classification based on minion kills.
    Riot API sometimes misclassifies laners as junglers.
    """
    if api_lane == 'JUNGLE' and neutral_cs < 15 and lane_cs > 50:
        # Clear signs of a laner, not a jungler - classify by role
        if role == 'SOLO':
            return 'TOP'
        elif role == 'CARRY':
            return 'BOTTOM'
        elif role == 'SUPPORT':
            return 'BOTTOM'
        else:
            return 'TOP'
    return api_lane

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

def get_champion_winrate(puuid, champion_name, current_match_won, current_match_id=None):
    """
    Get user's recent win rate on a specific champion in ranked games.
    Checks last 20 ranked matches per queue (Solo/Duo queue=420 + Flex queue=440).
    The current match result is seeded directly since it may not be indexed yet.
    current_match_id is excluded from the history loop to prevent double-counting.
    Returns a formatted string or None if no ranked games found on that champ.
    """
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')
    headers = {'X-Riot-Token': RIOT_API_KEY}

    match_ids = []

    # Fetch ranked solo/duo and flex match IDs (20 each, up to 40 total)
    for queue_id in [420, 440]:  # 420 = Ranked Solo/Duo, 440 = Ranked Flex
        url = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&start=0&count=20'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            match_ids.extend(response.json())

    # Deduplicate (preserve order)
    seen = set()
    unique_ids = []
    for m in match_ids:
        if m not in seen:
            seen.add(m)
            unique_ids.append(m)

    # Start with the current match result (handles API indexing delay)
    wins = 1 if current_match_won else 0
    total = 1

    for match_id in unique_ids:
        # Skip current match - already seeded above to avoid double-counting
        if current_match_id and match_id == current_match_id:
            continue
        url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue
        data = response.json()
        for participant in data.get('info', {}).get('participants', []):
            if participant['puuid'] == puuid:
                if participant.get('championName') == champion_name:
                    total += 1
                    if participant.get('win', False):
                        wins += 1
                break  # found our player, move to next match

    losses = total - wins
    win_rate = round((wins / total) * 100)
    return f"{wins}W / {losses}L ({win_rate}%) in last {total} ranked game{'s' if total != 1 else ''}"


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
    
    # Correct lane classification if misclassified by API
    neutral_minions = player_stats.get('neutralMinionsKilled', 0)
    lane_minions = player_stats.get('totalMinionsKilled', 0)
    player_role = player_stats.get('role', 'SOLO')
    lane = correct_lane_from_cs(lane, neutral_minions, lane_minions, player_role)
    
    # Additional performance stats with League terminology
    gold_per_minute = round(player_stats.get('challenges', {}).get('goldPerMinute', 0), 1)
    damage_per_minute = round(player_stats.get('challenges', {}).get('damagePerMinute', 0), 1)
    vision_score = player_stats.get('visionScore', 0)
    largest_spree = player_stats.get('largestKillingSpree', 0)
    cc_time = player_stats.get('totalTimeCCDealt', 0)
    wards_placed = player_stats.get('wardsPlaced', 0)
    wards_killed = player_stats.get('wardsKilled', 0)
    control_wards = player_stats.get('detectorWardsPlaced', 0)
    neutral_minions = player_stats.get('neutralMinionsKilled', 0)
    lane_minions = player_stats.get('totalMinionsKilled', 0)
    total_cs = neutral_minions + lane_minions

    return kda, score, damage, champ, totalMinionsKilled, victory, time_dead, kill_participation, game_mode, lane, time_ago, gold_per_minute, damage_per_minute, vision_score, largest_spree, cc_time, wards_placed, wards_killed, control_wards, neutral_minions, lane_minions, total_cs


def get_lane_comparison(puuid, match_data):
    """
    Compare user's lane performance with the enemy laner.
    Returns detailed stats for roasting comparison.
    """
    player_team_id = None
    user_lane = None
    user_stats = None
    
    # Get player info and correct their lane
    for participant in match_data.get('info', {}).get('participants', []):
        if participant['puuid'] == puuid:
            player_team_id = participant['teamId']
            api_lane = participant.get('lane', 'Unknown')
            neutral_cs = participant.get('neutralMinionsKilled', 0)
            lane_cs = participant.get('totalMinionsKilled', 0)
            role = participant.get('role', 'SOLO')
            user_lane = correct_lane_from_cs(api_lane, neutral_cs, lane_cs, role)
            user_stats = participant
            break
    
    if not user_stats or not user_lane or user_lane == 'Unknown':
        return None
    
    # Find enemy laner (opposite team, same lane)
    enemy_candidates = []
    for participant in match_data.get('info', {}).get('participants', []):
        if participant['teamId'] != player_team_id:
            # Correct enemy lane too
            api_lane = participant.get('lane', 'Unknown')
            neutral_cs = participant.get('neutralMinionsKilled', 0)
            lane_cs = participant.get('totalMinionsKilled', 0)
            role = participant.get('role', 'SOLO')
            corrected_lane = correct_lane_from_cs(api_lane, neutral_cs, lane_cs, role)
            
            if corrected_lane == user_lane:
                enemy_candidates.append(participant)
    
    if not enemy_candidates:
        return None
    
    # If multiple candidates, pick based on role (for accurate matchups)
    user_role = user_stats.get('role', 'NONE')
    
    if len(enemy_candidates) > 1:
        if user_lane == 'JUNGLE':
            # For jungle, pick the one with more camps
            enemy_stats = max(enemy_candidates, key=lambda x: x.get('neutralMinionsKilled', 0))
        else:
            # For other lanes, pick the one with matching role (SOLO, CARRY, SUPPORT)
            matching_role = [e for e in enemy_candidates if e.get('role') == user_role]
            if matching_role:
                enemy_stats = matching_role[0]
            else:
                # If no exact role match, just pick first
                enemy_stats = enemy_candidates[0]
    else:
        enemy_stats = enemy_candidates[0]
    
    # Calculate comparative metrics
    user_champ = user_stats.get('championName', 'Unknown')
    enemy_champ = enemy_stats.get('championName', 'Unknown')
    
    user_kda_value = user_stats['kills'] + user_stats['assists'] - (user_stats['deaths'] * 0.5)
    enemy_kda_value = enemy_stats['kills'] + enemy_stats['assists'] - (enemy_stats['deaths'] * 0.5)
    
    user_damage = user_stats.get('totalDamageDealtToChampions', 0)
    enemy_damage = enemy_stats.get('totalDamageDealtToChampions', 0)
    
    user_cs = user_stats.get('totalMinionsKilled', 0) + user_stats.get('neutralMinionsKilled', 0)
    enemy_cs = enemy_stats.get('totalMinionsKilled', 0) + enemy_stats.get('neutralMinionsKilled', 0)
    
    user_gold = user_stats.get('goldEarned', 0)
    enemy_gold = enemy_stats.get('goldEarned', 0)
    
    comparison = {
        'lane': user_lane,
        'user_champ': user_champ,
        'enemy_champ': enemy_champ,
        'user_kills': user_stats['kills'],
        'enemy_kills': enemy_stats['kills'],
        'user_deaths': user_stats['deaths'],
        'enemy_deaths': enemy_stats['deaths'],
        'user_assists': user_stats['assists'],
        'enemy_assists': enemy_stats['assists'],
        'user_damage': user_damage,
        'enemy_damage': enemy_damage,
        'user_cs': user_cs,
        'enemy_cs': enemy_cs,
        'user_gold': user_gold,
        'enemy_gold': enemy_gold,
        'user_kda_value': user_kda_value,
        'enemy_kda_value': enemy_kda_value,
    }
    
    return comparison


def generate_lane_roast(comparison):
    """
    Generate funny League-themed roasting commentary regardless of win/loss.
    """
    import random
    
    if not comparison:
        return None
    
    comp = comparison
    
    # Calculate diffs
    damage_diff = comp['user_damage'] - comp['enemy_damage']
    cs_diff = comp['user_cs'] - comp['enemy_cs']
    gold_diff = comp['user_gold'] - comp['enemy_gold']
    kda_diff = comp['user_kda_value'] - comp['enemy_kda_value']
    
    # Decide winner and generate commentary
    wins = 0
    if damage_diff > 0:
        wins += 1
    if cs_diff > 0:
        wins += 1
    if gold_diff > 0:
        wins += 1
    if kda_diff > 0:
        wins += 1
    
    # Generate roast based on performance
    if wins >= 3:
        # You're winning - sarcastic roast
        roasts = [
            f"wow {comp['user_champ']} finally stepped up 🎉 only {abs(damage_diff):,} damage ahead",
            f"congratulations on not getting gapped for once! {abs(cs_diff)} cs up",
            f"look at you actually winning a matchup... is {comp['enemy_champ']} afk?",
            f"diff too visible? more like diff too small: {abs(damage_diff):,} dmg",
            f"carry hard but you'll int next team fight anyway",
        ]
    elif wins <= 1:
        # You're losing - direct roast
        roasts = [
            f"{comp['enemy_champ']} is collecting your paycheck: {abs(damage_diff):,} dmg gap",
            f"turbo diff'd by {comp['enemy_champ']} - down {abs(cs_diff)} cs and {abs(damage_diff):,} dmg",
            f"get gapped harder: {abs(gold_diff):,} gold down to {comp['enemy_champ']}",
            f"that's not a matchup difference, that's a SKILL difference",
            f"{comp['enemy_champ']} just collected your LP for the day",
            f"literally just deleted your lane",
        ]
    else:
        # Close game - mixed roast
        roasts = [
            f"somehow basically equal with {comp['enemy_champ']}... that's concerning",
            f"coin flip merchant energy: {comp['user_champ']} vs {comp['enemy_champ']}",
            f"it's almost matching... almost like you both belong in this elo",
            f"basically the same? both equally mid then",
        ]
    
    roast = random.choice(roasts)
    
    # Determine damage color indicators
    if comp['user_damage'] > comp['enemy_damage']:
        user_dmg_indicator = "🟢"
        enemy_dmg_indicator = "🔴"
    elif comp['user_damage'] < comp['enemy_damage']:
        user_dmg_indicator = "🔴"
        enemy_dmg_indicator = "🟢"
    else:
        user_dmg_indicator = "⚪"
        enemy_dmg_indicator = "⚪"
    
    # Add detailed stats
    comparison_text = (
        f"🎯 **LANE COMPARISON ({comp['lane'].upper()})**\n"
        f"**You:** {comp['user_champ']} {comp['user_kills']}/{comp['user_deaths']}/{comp['user_assists']} "
        f"| {user_dmg_indicator} {comp['user_damage']:,} DMG | {comp['user_cs']} CS\n"
        f"**Enemy:** {comp['enemy_champ']} {comp['enemy_kills']}/{comp['enemy_deaths']}/{comp['enemy_assists']} "
        f"| {enemy_dmg_indicator} {comp['enemy_damage']:,} DMG | {comp['enemy_cs']} CS\n"
        f"**Verdict:** {roast}"
    )
    
    return comparison_text