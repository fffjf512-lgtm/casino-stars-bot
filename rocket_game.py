import random
import asyncio
from config import CRASH_POINTS


def get_crash_point() -> float:
    roll = random.random()
    for multiplier, cumulative_prob in CRASH_POINTS:
        if roll <= cumulative_prob:
            return multiplier
    return CRASH_POINTS[-1][0]


def calculate_payout(bet: int, multiplier: float) -> int:
    return int(bet * multiplier)


class RocketGame:
    def __init__(self):
        self.active_games = {}

    async def start_game(self, user_id: int, bet: int):
        crash_point = get_crash_point()
        game_id = f"{user_id}_{random.randint(1000, 9999)}"
        
        self.active_games[game_id] = {
            "user_id": user_id,
            "bet": bet,
            "crash_point": crash_point,
            "current_multiplier": 1.0,
            "status": "flying",
            "cashout_multiplier": None
        }
        return game_id, crash_point

    async def fly(self, game_id: str):
        game = self.active_games.get(game_id)
        if not game:
            return None
        
        steps = []
        multiplier = 1.0
        
        while multiplier < game["crash_point"]:
            multiplier = round(multiplier + random.uniform(0.05, 0.15), 2)
            if multiplier > game["crash_point"]:
                multiplier = game["crash_point"]
            game["current_multiplier"] = multiplier
            steps.append(multiplier)
            await asyncio.sleep(0.3)
        
        game["status"] = "crashed"
        return steps

    def cashout(self, game_id: str):
        game = self.active_games.get(game_id)
        if not game or game["status"] != "flying":
            return None
        
        game["status"] = "cashed_out"
        game["cashout_multiplier"] = game["current_multiplier"]
        return calculate_payout(game["bet"], game["current_multiplier"])

    def get_game(self, game_id: str):
        return self.active_games.get(game_id)

    def remove_game(self, game_id: str):
        if game_id in self.active_games:
            del self.active_games[game_id]


rocket_game = RocketGame()
