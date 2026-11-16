
from sqlalchemy import text
from conftest import TestingSessionLocal
from models import Player


def test_player_model_query_uses_isolated_database(seed_test_players):
    with TestingSessionLocal() as db:
        assert db.scalar(text('SELECT current_database()')) == 'scoutiq_test'
        players = db.query(Player).order_by(Player.id).all()
        assert [player.name for player in players] == ['Erling Haaland', 'Lionel Messi', 'Nicolo Barella']
