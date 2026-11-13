from fastapi import FastAPI, HTTPException, Depends

from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Player

app = FastAPI(title="ScoutIQ", version="1.0.0")

# Player dataset
players = [
    {"id": 1, "name": "Erling Haaland", "age": 26, "position": "ST", "club": "M. City", "goals": 20, "assists": 5, "minutes_played": 1800},
    {"id": 2, "name": "Lionel Messi", "age": 38, "position": "CAM", "club": "Inter Miami", "goals": 18, "assists": 9, "minutes_played": 1750},
    {"id": 3, "name": "Cristiano Ronaldo", "age": 41, "position": "ST", "club": "Al Nassr", "goals": 23, "assists": 19, "minutes_played": 1950},
    {"id": 4, "name": "Lautaro Martinez", "age": 29, "position": "ST", "club": "Inter Milan", "goals": 25, "assists": 7, "minutes_played": 2000},
    {"id": 5, "name": "Nicolo Barella", "age": 28, "position": "CM", "club": "Inter Milan", "goals": 8, "assists": 9, "minutes_played": 1890},
]


# REUSABLE FUNCTIONS

def find_player(player_id: int):
    for player in players:
        if player["id"] == player_id:
            return player

    raise HTTPException(
        status_code=404,
        detail=f"Player with ID {player_id} not found"
    )


def calculate_stats(player):
    minutes = player["minutes_played"]

    if minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Minutes played must be greater than zero"
        )

    return {
        "id": player["id"],
        "name": player["name"],
        "goals_per_90": round(player["goals"] * 90 / minutes, 2),
        "assists_per_90": round(player["assists"] * 90 / minutes, 2),
        "goal_contributions_per_90": round(
            (player["goals"] + player["assists"]) * 90 / minutes, 2
        )
    }


# HOME

@app.get("/")
def home():
    return {"message": "Welcome to ScoutIQ"}


# GET ALL PLAYERS

@app.get("/players")
def get_players(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    return {"players": players}
    


# COUNT PLAYERS

@app.get("/players/count")
def players_count(db: Session = Depends(get_db)):
    count = db.query(Player).count()
    return {"count": count}


# FILTER PLAYERS

@app.get("/players/filter")
def filter_players(
    position: str | None = None,
    club: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    db: Session = Depends(get_db)
):
    if min_age is not None and min_age < 0:
        raise HTTPException(
            status_code=400,
            detail="Minimum age cannot be negative"
        )

    if max_age is not None and max_age < 0:
        raise HTTPException(
            status_code=400,
            detail="Maximum age cannot be negative"
        )

    if min_age is not None and max_age is not None:
        if min_age > max_age:
            raise HTTPException(
                status_code=400,
                detail="Minimum age cannot be greater than maximum age"
            )

    query = db.query(Player)

    if position is not None:
        query = query.filter(
            func.lower(Player.position) == position.lower()
        )
    if club is not None:
        query = query.filter(
            func.lower(Player.club) == club.lower()
        )
    if min_age is not None:
        query = query.filter(
            Player.age >= min_age
        )    
    if max_age is not None:
        query = query.filter(
            Player.age <= max_age
        )

    return query.all()

# SORT PLAYERS

@app.get("/players/sort")
def sort_players(sort_by: str = "goals", order: str = "desc"):

    if sort_by not in ["goals", "assists", "age"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sorting field"
        )

    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sorting order"
        )

    return sorted(
        players,
        key=lambda player: player[sort_by],
        reverse=(order == "desc")
    )


# PLAYER RANKINGS

@app.get("/players/rankings")
def player_rankings(
    metric: str = "goals_per_90",
    position: str | None = None,
    min_minutes: int = 0
):

    supported_metrics = [
        "goals_per_90",
        "assists_per_90",
        "goal_contributions_per_90"
    ]

    # Validate metric
    if metric not in supported_metrics:
        raise HTTPException(
            status_code=400,
            detail="Invalid ranking metric"
        )

    # Validate minimum minutes
    if min_minutes < 0:
        raise HTTPException(
            status_code=400,
            detail="Minimum minutes cannot be negative"
        )

    ranking_list = []

    for player in players:

        # Filter by position
        if position is not None:
            if player["position"].casefold() != position.casefold():
                continue

        # Exclude players with insufficient minutes
        if player["minutes_played"] < min_minutes:
            continue

        # Exclude zero or negative minutes
        if player["minutes_played"] <= 0:
            continue

        # Calculate player statistics
        stats = calculate_stats(player)

        ranking_list.append({
            "player_id": player["id"],
            "name": player["name"],
            "value": stats[metric]
        })

    # Sort highest to lowest
    ranking_list.sort(
        key=lambda player: player["value"],
        reverse=True
    )

    # Assign sequential ranks
    for index, player in enumerate(ranking_list, start=1):
        player["rank"] = index

    return {
        "metric": metric,
        "rankings": ranking_list
    }


# COMPARE PLAYERS

@app.get("/players/compare")
def compare_players(player1: int, player2: int):

    if player1 == player2:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a player with themselves"
        )

    first_player = find_player(player1)
    second_player = find_player(player2)

    stats1 = calculate_stats(first_player)
    stats2 = calculate_stats(second_player)

    goals90_1 = (
        first_player["goals"] * 90
        / first_player["minutes_played"]
    )

    goals90_2 = (
        second_player["goals"] * 90
        / second_player["minutes_played"]
    )

    if goals90_1 > goals90_2:
        better_goalscorer = first_player["name"]
    elif goals90_1 < goals90_2:
        better_goalscorer = second_player["name"]
    else:
        better_goalscorer = "Tie"

    return {
        "player1": stats1,
        "player2": stats2,
        "comparison": {
            "better_goalscorer": better_goalscorer
        }
    }


# PLAYER STATS PER 90

@app.get("/players/{player_id}/stats")
def get_player_stats_per_90_min(player_id: int):

    player = find_player(player_id)
    return calculate_stats(player)


# GET PLAYER BY ID

@app.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):

    player = db.query(Player).filter(
        Player.id == player_id
    ).first()

    if player is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found"
        )
    return player
    