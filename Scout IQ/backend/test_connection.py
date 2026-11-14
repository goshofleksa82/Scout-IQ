"""ScoutIQ Step 21: 39 targeted checks + existing smoke tests.

Assumed API contracts: /players -> {'players': [...]}; sort -> list;
rankings -> {'rankings': [{'name','value','rank', ...}]}; stats ->
{'goals_per_90', 'assists_per_90', 'goal_contributions_per_90'}.
Adjust assertions if your main.py intentionally uses different JSON keys.
"""
import os
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from conftest import TestingSessionLocal, test_engine
from models import Player


def get_players(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list), f'Expected list from {path}: {data}'
    return data


def get_rankings(client, **params):
    response = client.get('/players/rankings', params=params)
    assert response.status_code == 200, response.text
    return response.json()['rankings']


def add_player(player):
    db = TestingSessionLocal()
    try:
        db.add(player)
        db.commit()
    finally:
        db.close()


# 1. FILTERING: 9 tests

def test_filter_position(client, seed_test_players):
    players = get_players(client, '/players/filter?position=ST')
    assert [p['name'] for p in players] == ['Erling Haaland']


def test_filter_club(client, seed_test_players):
    players = get_players(client, '/players/filter?club=Inter%20Miami')
    assert [p['name'] for p in players] == ['Lionel Messi']


def test_filter_position_case_insensitive(client, seed_test_players):
    assert [p['name'] for p in get_players(client, '/players/filter?position=st')] == ['Erling Haaland']


def test_filter_club_case_insensitive(client, seed_test_players):
    assert [p['name'] for p in get_players(client, '/players/filter?club=inter%20miami')] == ['Lionel Messi']


def test_filter_min_age(client, seed_test_players):
    assert {p['name'] for p in get_players(client, '/players/filter?min_age=30')} == {'Lionel Messi'}


def test_filter_max_age(client, seed_test_players):
    assert {p['name'] for p in get_players(client, '/players/filter?max_age=28')} == {'Erling Haaland', 'Nicolo Barella'}


def test_filter_negative_min_age(client):
    assert client.get('/players/filter?min_age=-1').status_code == 400


def test_filter_negative_max_age(client):
    assert client.get('/players/filter?max_age=-1').status_code == 400


def test_filter_invalid_age_range(client):
    assert client.get('/players/filter?min_age=40&max_age=20').status_code == 400


# 2. SORTING: 6 tests

def test_sort_goals_desc(client, seed_test_players):
    assert [p['goals'] for p in get_players(client, '/players/sort?sort_by=goals&order=desc')] == [20, 18, 8]


def test_sort_goals_asc(client, seed_test_players):
    assert [p['goals'] for p in get_players(client, '/players/sort?sort_by=goals&order=asc')] == [8, 18, 20]


def test_sort_assists_desc(client, seed_test_players):
    assert [p['assists'] for p in get_players(client, '/players/sort?sort_by=assists&order=desc')] == [9, 9, 5]


def test_sort_age_asc(client, seed_test_players):
    assert [p['age'] for p in get_players(client, '/players/sort?sort_by=age&order=asc')] == [26, 28, 38]


def test_sort_invalid_field(client):
    assert client.get('/players/sort?sort_by=height&order=asc').status_code == 400


def test_sort_invalid_order(client):
    assert client.get('/players/sort?sort_by=goals&order=sideways').status_code == 400


# 3. STATS: 5 tests

def test_stats_goals_per_90(client, seed_test_players):
    r = client.get('/players/1/stats')
    assert r.status_code == 200
    assert r.json()['goals_per_90'] == pytest.approx(1.00, abs=0.01)


def test_stats_assists_per_90(client, seed_test_players):
    r = client.get('/players/1/stats')
    assert r.status_code == 200
    assert r.json()['assists_per_90'] == pytest.approx(0.25, abs=0.01)


def test_stats_contributions_per_90(client, seed_test_players):
    r = client.get('/players/1/stats')
    assert r.status_code == 200
    assert r.json()['goal_contributions_per_90'] == pytest.approx(1.25, abs=0.01)


def test_stats_not_found(client):
    assert client.get('/players/999/stats').status_code == 404


def test_stats_zero_minutes(client, zero_minute_player):
    assert client.get('/players/4/stats').status_code == 400


# 4. COMPARISON: 6 tests

def comparison(client, p1=1, p2=2):
    r = client.get('/players/compare', params={'player1': p1, 'player2': p2})
    assert r.status_code == 200, r.text
    return r.json()


def comparison_players(data):
    # Existing ScoutIQ implementation typically returns player1 and player2.
    assert 'player1' in data and 'player2' in data, data
    return data['player1'], data['player2']


def test_compare_haaland_messi(client, seed_test_players):
    p1, p2 = comparison_players(comparison(client))
    assert p1['name'] == 'Erling Haaland'
    assert p2['name'] == 'Lionel Messi'


def test_compare_player_information(client, seed_test_players):
    p1, p2 = comparison_players(comparison(client))
    assert (p1['club'], p1['position'], p1['goals']) == ('Manchester City', 'ST', 20)
    assert (p2['club'], p2['position'], p2['goals']) == ('Inter Miami', 'CAM', 18)


def test_compare_per90(client, seed_test_players):
    p1, p2 = comparison_players(comparison(client))
    assert p1['goals_per_90'] == pytest.approx(1.0, abs=0.01)
    assert p2['goal_contributions_per_90'] == pytest.approx(27 * 90 / 1750, abs=0.01)


def test_compare_same_id(client):
    assert client.get('/players/compare?player1=1&player2=1').status_code == 400


def test_compare_missing_id(client, seed_test_players):
    assert client.get('/players/compare?player1=1&player2=999').status_code == 404


def test_compare_zero_minutes(client, zero_minute_player):
    _, p2 = comparison_players(comparison(client, 1, 4))
    assert p2['goals_per_90'] is None
    assert p2['assists_per_90'] is None
    assert p2['goal_contributions_per_90'] is None


# 5. RANKINGS: 9 tests

def ranking_names(client, metric, **kwargs):
    return [p['name'] for p in get_rankings(client, metric=metric, **kwargs)]


def test_rank_goals_per90(client, seed_test_players):
    assert ranking_names(client, 'goals_per_90') == ['Erling Haaland', 'Lionel Messi', 'Nicolo Barella']


def test_rank_assists_per90(client, seed_test_players):
    assert ranking_names(client, 'assists_per_90') == ['Lionel Messi', 'Nicolo Barella', 'Erling Haaland']


def test_rank_contributions_per90(client, seed_test_players):
    assert ranking_names(client, 'goal_contributions_per_90') == ['Lionel Messi', 'Erling Haaland', 'Nicolo Barella']


def test_rank_position(client, seed_test_players):
    assert ranking_names(client, 'goals_per_90', position='ST') == ['Erling Haaland']


def test_rank_min_minutes(client, seed_test_players):
    assert ranking_names(client, 'goals_per_90', min_minutes=1800) == ['Erling Haaland', 'Nicolo Barella']


def test_rank_invalid_metric(client):
    assert client.get('/players/rankings?metric=height').status_code == 400


def test_rank_negative_min_minutes(client):
    assert client.get('/players/rankings?metric=goals_per_90&min_minutes=-1').status_code == 400


def test_rank_excludes_zero_minutes(client, zero_minute_player):
    assert 'Zero Minutes' not in ranking_names(client, 'goals_per_90')


def test_rank_descending_and_sequential(client, seed_test_players):
    rankings = get_rankings(client, metric='goals_per_90')
    values = [p['value'] for p in rankings]
    assert values == sorted(values, reverse=True)
    assert [p['rank'] for p in rankings] == list(range(1, len(rankings) + 1))


# 6. RETRIEVAL & ISOLATION: 4 tests

def test_get_player_by_id(client, seed_test_players):
    r = client.get('/players/1')
    assert r.status_code == 200
    assert r.json()['name'] == 'Erling Haaland'


def test_player_not_found(client):
    assert client.get('/players/999').status_code == 404


def test_fresh_database_has_only_seeded_players(client, seed_test_players):
    # Independent test: verifies a fresh fixture has only the 3 seed records.
    r = client.get('/players')
    assert r.status_code == 200
    assert {p['id'] for p in r.json()['players']} == {1, 2, 3}


def test_test_database_is_separate_from_development(client, seed_test_players):
    # Verifies isolation by configuration + live connection, without touching dev data.
    with test_engine.connect() as connection:
        assert connection.execute(text('SELECT current_database()')).scalar_one() == 'scoutiq_test'
    dev_url = os.getenv('DATABASE_URL')
    if dev_url:
        assert make_url(dev_url).database != 'scoutiq_test'
    add_player(Player(id=5, name='Temporary Player', age=20, position='ST', club='Test FC', goals=1, assists=0, minutes_played=90))
    r = client.get('/players')
    assert r.status_code == 200
    assert {p['id'] for p in r.json()['players']} == {1, 2, 3, 5}


# EXISTING SMOKE TESTS (additional to the 39 checks)

def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    assert r.json()['message'] == 'Welcome to ScoutIQ'


def test_get_all_players_from_database(client, seed_test_players):
    r = client.get('/players')
    assert r.status_code == 200
    data = r.json()
    assert 'players' in data
    assert len(data['players']) == 3
    assert 'Erling Haaland' in [p['name'] for p in data['players']]

# STEP 22: RESPONSE SCHEMA VALIDATION

from pydantic import ValidationError
from schemas import PlayerResponse, PlayerRankingsResponse, PlayerComparisonResponse


def test_player_response_schema(client, seed_test_players):
    response = client.get('/players/1')
    assert response.status_code == 200
    player = response.json()
    assert set(player) == {'id', 'name', 'age', 'position', 'club', 'goals', 'assists', 'minutes_played'}
    assert type(player['id']) is int
    assert type(player['age']) is int
    assert type(player['goals']) is int
    assert type(player['assists']) is int
    assert type(player['minutes_played']) is int
    PlayerResponse.model_validate(player)


def test_stats_response_schema(client, seed_test_players):
    response = client.get('/players/1/stats')
    assert response.status_code == 200
    data = response.json()
    assert data['player_id'] == 1
    assert data['name'] == 'Erling Haaland'
    assert type(data['goals_per_90']) is float
    assert type(data['assists_per_90']) is float
    assert type(data['goal_contributions_per_90']) is float


def test_comparison_nullable_stats_schema(client, zero_minute_player):
    response = client.get('/players/compare?player1=1&player2=4')
    assert response.status_code == 200
    data = PlayerComparisonResponse.model_validate(response.json())
    assert data.player2.minutes_played == 0
    assert data.player2.goals_per_90 is None
    assert data.player2.assists_per_90 is None
    assert data.player2.goal_contributions_per_90 is None


def test_rankings_response_schema(client, seed_test_players):
    response = client.get('/players/rankings?metric=goals_per_90')
    assert response.status_code == 200
    data = PlayerRankingsResponse.model_validate(response.json())
    assert data.metric == 'goals_per_90'
    assert len(data.rankings) == 3
    assert [p.rank for p in data.rankings] == [1, 2, 3]
    assert all(type(p.value) is float for p in data.rankings)


@pytest.mark.parametrize('changes', [
    {'goals': -1},
    {'age': -1},
    {'assists': -1},
    {'minutes_played': -1},
    {'name': ''},
    {'name': '   '},
    {'position': ''},
    {'club': '   '},
])
def test_invalid_player_response_rejected(changes):
    valid = {
        'id': 1, 'name': 'Test Player', 'age': 24, 'position': 'ST',
        'club': 'Test FC', 'goals': 3, 'assists': 1, 'minutes_played': 900,
    }
    with pytest.raises(ValidationError):
        PlayerResponse.model_validate({**valid, **changes})
