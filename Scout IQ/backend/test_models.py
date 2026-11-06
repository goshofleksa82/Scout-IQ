
from database import SessionLocal
from models import Player

db = SessionLocal()

try:
    players = db.query(Player).all()

    for player in players:
        print(f"{player.name} | {player.club} | {player.goals} goals")

finally:
    db.close()
