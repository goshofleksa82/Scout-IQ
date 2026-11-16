import pytest
from conftest import TestingSessionLocal
from models import Player


@pytest.fixture
def history_data(admin_client, seed_test_players):
    season = admin_client.post('/seasons', json={'name':'Demo 2026','starts_on':'2026-01-01','ends_on':'2026-12-31'}).json()
    club = admin_client.post('/clubs', json={'name':'Transfer Demo FC'}).json()
    with TestingSessionLocal() as db: old_club = db.get(Player,1).club_id
    return season['id'], club['id'], old_club


def test_transfer_tracks_previous_and_current_clubs(admin_client, history_data):
    season, new, old = history_data
    assert admin_client.post('/players/1/memberships',json={'club_id':old,'season_id':season,'joined_on':'2026-01-01'}).status_code == 201
    response = admin_client.post('/players/1/transfers',json={'club_id':new,'season_id':season,'transfer_date':'2026-07-01'})
    assert response.status_code == 201 and response.json()['previous_club_id'] == old
    history = admin_client.get('/players/1/memberships').json()
    assert history[0]['left_on'] == '2026-07-01' and history[1]['joined_on'] == '2026-07-01'
    assert admin_client.get('/players/1').json()['club'] == 'Transfer Demo FC'
    assert admin_client.get(f'/players/history/search?club_id={old}&on_date=2026-06-30').json()['total'] == 1
    assert admin_client.get(f'/players/history/search?club_id={old}&on_date=2026-07-01').json()['total'] == 0
    assert admin_client.get(f'/players/history/search?club_id={new}&on_date=2026-07-01').json()['total'] == 1


def test_database_prevents_overlapping_memberships(admin_client, history_data):
    season, new, old = history_data
    assert admin_client.post('/players/1/memberships',json={'club_id':old,'season_id':season,'joined_on':'2026-01-01','left_on':'2026-07-01'}).status_code == 201
    assert admin_client.post('/players/1/memberships',json={'club_id':new,'season_id':season,'joined_on':'2026-06-01'}).status_code == 409
    assert admin_client.post('/players/1/memberships',json={'club_id':new,'season_id':season,'joined_on':'2026-07-01'}).status_code == 201
    assert admin_client.patch('/players/1',json={'club':'Bypass'}).status_code == 409


def test_season_and_membership_boundaries(admin_client, history_data):
    season, new, old = history_data
    assert admin_client.post('/seasons',json={'name':'Bad','starts_on':'2026-12-31','ends_on':'2026-01-01'}).status_code == 422
    assert admin_client.post('/players/1/memberships',json={'club_id':new,'season_id':season,'joined_on':'2025-12-31'}).status_code == 400
    assert admin_client.post('/players/1/memberships',json={'club_id':new,'season_id':season,'joined_on':'2026-12-31'}).status_code == 201
    assert admin_client.get(f'/players/history/search?season_id={season}').json()['total'] == 1
    assert admin_client.get(f'/players/history/search?season_id={season}&on_date=2025-12-31').status_code == 400


def test_transfers_reject_invalid_foreign_keys_and_require_admin(client, admin_client, history_data):
    season, new, old = history_data
    assert admin_client.post('/players/1/transfers',json={'club_id':999,'season_id':season,'transfer_date':'2026-07-01'}).status_code == 404
    admin_client.headers.pop('Authorization')
    assert client.post('/players/1/transfers',json={'club_id':new,'season_id':season,'transfer_date':'2026-07-01'}).status_code == 401
