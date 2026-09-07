BOT_TOKEN = "8991377045:AAHt8HZ-1Ms6WDuxTSb18FkjXQEPR8uKoFc"

# Rocket game settings
HOUSE_EDGE = 0.05  # 5% house edge
MAX_MULTIPLIER = 50.0
MIN_BET = 1
MAX_BET = 1000

# Multiplier chances (cumulative probability)
# Each entry: (multiplier, cumulative_probability)
# Higher multiplier = lower chance
CRASH_POINTS = [
    (1.0, 0.03),    # 3% instant crash
    (1.1, 0.15),    # 12% chance to reach 1.1x
    (1.2, 0.25),    # 10% chance to reach 1.2x
    (1.5, 0.45),    # 20% chance to reach 1.5x
    (1.8, 0.58),    # 13% chance to reach 1.8x
    (2.0, 0.68),    # 10% chance to reach 2.0x
    (2.5, 0.78),    # 10% chance to reach 2.5x
    (3.0, 0.85),    # 7% chance to reach 3.0x
    (5.0, 0.92),    # 7% chance to reach 5.0x
    (10.0, 0.96),   # 4% chance to reach 10.0x
    (20.0, 0.985),  # 2.5% chance to reach 20.0x
    (50.0, 1.0),    # 1.5% chance to reach 50.0x
]
