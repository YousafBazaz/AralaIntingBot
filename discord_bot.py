import os
import discord
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from riot_api import get_puuid, get_latest_match_id, get_match_stats, get_lane_comparison, generate_lane_roast, get_champion_winrate

def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

class AralaBot(discord.Client):
    def __init__(self, channel_ids, summoner_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_ids = channel_ids
        self.summoner_name = summoner_name
        self.last_match_id = self.load_last_match_id()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def load_last_match_id(self):
        try:
            with open("last_match_id.txt", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def save_last_match_id(self, match_id):
        with open("last_match_id.txt", "w") as f:
            f.write(match_id)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.loop.create_task(self.check_for_new_match())

    async def check_for_new_match(self):
        await self.wait_until_ready()
        channels = [self.get_channel(cid) for cid in self.channel_ids]
        
        loop = asyncio.get_event_loop()
        
        try:
            puuid = await loop.run_in_executor(self.executor, get_puuid)
            print("PUUID:", puuid)
        except Exception as e:
            print(f"Error getting PUUID: {e}")
            for channel in channels:
                if channel:
                    await channel.send(f"Error: Could not get PUUID. Check API key and summoner name.")
            return
            
        if not puuid:
            for channel in channels:
                if channel:
                    await channel.send(f"Could not find PUUID for {self.summoner_name}. Check the summoner name and region.")
            return
        while not self.is_closed():
            try:
                latest_match = await loop.run_in_executor(self.executor, get_latest_match_id, puuid)
                if latest_match and latest_match != self.last_match_id:
                    self.last_match_id = latest_match
                    self.save_last_match_id(latest_match)  # Save to file
                    
                    # Get match data
                    import requests
                    RIOT_API_KEY = os.getenv('RIOT_API_KEY')
                    match_url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{latest_match}'
                    headers = {'X-Riot-Token': RIOT_API_KEY}
                    
                    def get_match_data():
                        response = requests.get(match_url, headers=headers, timeout=30)
                        return response.json()
                    
                    match_data = await loop.run_in_executor(self.executor, get_match_data)
                    queue_id = match_data.get('info', {}).get('queueId')
                    
                    kda, score, damage, champ, totalMinionsKilled, victory, time_dead, kill_participation, game_mode, lane, time_ago, gold_per_minute, damage_per_minute, vision_score, largest_spree, cc_time, wards_placed, wards_killed, control_wards, neutral_minions, lane_minions, total_cs = await loop.run_in_executor(self.executor, get_match_stats, puuid, latest_match)
                    
                    # Get champion win rate (ranked only)
                    current_match_won = victory == "Victory"
                    champ_winrate = await loop.run_in_executor(self.executor, get_champion_winrate, puuid, champ, current_match_won, latest_match, queue_id)
                    champ_winrate_line = f"\nChamp Win Rate: {champ_winrate}" if champ_winrate else ""

                    # Get lane comparison and roast
                    lane_comp = await loop.run_in_executor(self.executor, get_lane_comparison, puuid, match_data)
                    lane_roast = ""
                    if lane_comp:
                        lane_roast = f"\n\n{await loop.run_in_executor(self.executor, generate_lane_roast, lane_comp)}"
                    
                    mention_user_id = os.getenv('MENTION_USER_ID')
                    mention = f"<@{mention_user_id}>" if mention_user_id else self.summoner_name
                    message = (
                        f"{mention} just finished a new match!\n"
                        f"Result: {victory}\n"
                        f"Game Mode: {game_mode}\n"
                        f"Lane: {lane}\n"
                        f"Champion: {champ}{champ_winrate_line}\n\n"
                        f"**━━ COMBAT STATS ━━**\n"
                        f"KDA: {kda}\n"
                        f"Level: {score}\n"
                        f"Kill Participation: {kill_participation}%\n"
                        f"Best Streak: {largest_spree} kills\n\n"
                        f"**━━ DAMAGE & ECONOMY ━━**\n"
                        f"Damage to Champions: {damage:,}\n"
                        f"DPM (Damage/Min): {damage_per_minute}\n"
                        f"Gold/Min: {gold_per_minute}\n\n"
                        f"**━━ RESOURCE CONTROL ━━**\n"
                        f"Jungle CS: {neutral_minions}\n"
                        f"Lane CS: {lane_minions}\n"
                        f"Vision Score: {vision_score}\n"
                        f"Wards: {wards_placed} Placed | {wards_killed} Destroyed\n"
                        f"Control Wards: {control_wards} Placed\n"
                        f"CC Time: {cc_time}s\n\n"
                        f"**━━ SURVIVAL ━━**\n"
                        f"Time Dead: {time_dead}s\n"
                        f"Last played: {time_ago}"
                        f"{lane_roast}"
                    )
                    for channel in channels:
                        if channel:
                            try:
                                await channel.send(message)
                            except Exception as e:
                                print(f"Error sending message to channel: {e}")
            except Exception as e:
                print(f"Error processing match: {e}")
                
            await asyncio.sleep(10)