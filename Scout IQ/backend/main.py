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


def get_comparison_stats(player: Player):
    stats = {
        "name": player.name,
        "club": player.club,
        "position": player.position,
        "goals": player.goals,
        "assists": player.assists,
        "minutes_played": player.minutes_played,
        "goals_per_90": None,
        "assists_per_90": None,
        "goal_contributions_per_90": None
    }

    if player.minutes_played > 0:
        stats["goals_per_90"] = round(
            player.goals * 90 / player.minutes_played, 2
        )

        stats["assists_per_90"] = round(
            player.assists * 90 / player.minutes_played, 2
        )

        stats["goal_contributions_per_90"] = round(
            (player.goals + player.assists) * 90
            / player.minutes_played, 2
        )

    return stats

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
def sort_players(
    sort_by: str = "goals", 
    order: str = "desc",
    db: Session = Depends(get_db)
    ):

    allowed_fields = ["goals", "assists", "age"]

    if sort_by not in allowed_fields:
        raise HTTPException(
            status_code=400,
            detail="Invalid sorting field"
        )

    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sorting order"
        )

    column = getattr(Player, sort_by)

    if order == "asc":
        query = db.query(Player).order_by(column.asc())
    else:
        query = db.query(Player).order_by(column.desc())    

    return query.all()

# PLAYER RANKINGS



@app.get("/players/rankings")
def get_player_rankings(
    metric: str = "goals_per_90",
    position: str | None = None,
    min_minutes: int = 0,
    db: Session = Depends(get_db)
):
    allowed_metrics = [
        "goals_per_90",
        "assists_per_90",
        "goal_contributions_per_90"
    ]

    # Validate parameters
    if metric not in allowed_metrics:
        raise HTTPException(
            status_code=400,
            detail="Invalid ranking metric"
        )

    if min_minutes < 0:
        raise HTTPException(
            status_code=400,
            detail="Minimum minutes cannot be negative"
        )

    # Retrieve eligible players from PostgreSQL
    query = db.query(Player).filter(
        Player.minutes_played > 0,
        Player.minutes_played >= min_minutes
    )

    # Optional position filter
    if position is not None:
        query = query.filter(
            func.lower(Player.position) == position.lower()
        )

    players = query.all()

    # Calculate rankings
    rankings = []

    for player in players:
        if metric == "goals_per_90":
            value = player.goals * 90 / player.minutes_played

        elif metric == "assists_per_90":
            value = player.assists * 90 / player.minutes_played

        else:
            value = (
                (player.goals + player.assists) * 90
                / player.minutes_played
            )

        rankings.append({
            "player_id": player.id,
            "name": player.name,
            "position": player.position,
            "value": value
        })

    # Sort by unrounded values, highest first
    rankings.sort(
        key=lambda player: player["value"],
        reverse=True
    )

    # Assign ranks and round displayed values
    for rank, player in enumerate(rankings, start=1):
        player["rank"] = rank
        player["value"] = round(player["value"], 2)

    return {
        "metric": metric,
        "rankings": rankings
    }




# COMPARE PLAYERS


@app.get("/players/compare")
def compare_players(
    player1: int,
    player2: int,
    db: Session = Depends(get_db)
):
    # Validate IDs
    if player1 == player2:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a player with themselves"
        )

    # Retrieve both players from PostgreSQL
    first_player = db.query(Player).filter(
        Player.id == player1
    ).first()

    second_player = db.query(Player).filter(
        Player.id == player2
    ).first()

    # Check if both players exist
    if first_player is None or second_player is None:
        raise HTTPException(
            status_code=404,
            detail="One or both players not found"
        )

    return {
        "player1": get_comparison_stats(first_player),
        "player2": get_comparison_stats(second_player)
    }



# PLAYER STATS PER 90


@app.get("/players/{player_id}/stats")
def get_player_stats(
    player_id: int,
    db: Session = Depends(get_db)
):
    # Retrieve player from PostgreSQL
    player = db.query(Player).filter(
        Player.id == player_id
    ).first()

    # Check if player exists
    if player is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found"
        )

    # Prevent division by zero
    if player.minutes_played <= 0:
        raise HTTPException(
            status_code=400,
            detail="Player has no minutes played"
        )

    # Calculate statistics
    goals_per_90 = round(
        (player.goals * 90) / player.minutes_played, 2
    )

    assists_per_90 = round(
        (player.assists * 90) / player.minutes_played, 2
    )

    goal_contributions_per_90 = round(
        ((player.goals + player.assists) * 90)
        / player.minutes_played, 2
    )

    return {
        "player_id": player.id,
        "name": player.name,
        "goals_per_90": goals_per_90,
        "assists_per_90": assists_per_90,
        "goal_contributions_per_90": goal_contributions_per_90
    }


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
    