"""Composable player queries with literal substring name matching."""
from sqlalchemy import func
from app.models import Player
from app.schemas import PlayerSearch
from app.repositories.pagination import paginate


def search_players(db, filters: PlayerSearch):
    query = db.query(Player)
    if filters.name is not None:
        query = query.filter(func.lower(Player.name).contains(filters.name.lower(), autoescape=True))
    for name in ("position", "club"):
        value = getattr(filters, name)
        if value is not None:
            query = query.filter(func.lower(getattr(Player, name)) == value.lower())
    for name, column in (("age", Player.age), ("goals", Player.goals), ("assists", Player.assists), ("minutes", Player.minutes_played)):
        low, high = getattr(filters, "min_" + name), getattr(filters, "max_" + name)
        if low is not None: query = query.filter(column >= low)
        if high is not None: query = query.filter(column <= high)
    column = getattr(Player, filters.sort_by)
    if filters.sort_by == "name": column = func.lower(column)
    query = query.order_by(column.asc() if filters.order == "asc" else column.desc(), Player.id)
    return paginate(query, filters.page, filters.page_size)


def ordered_players(db):
    return db.query(Player).order_by(Player.id)


def player_by_id(db, player_id):
    return db.get(Player, player_id)
