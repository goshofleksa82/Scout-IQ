import pytest
from conftest import TestingSessionLocal
from models import Club, Player


def test_competition_and_club_relationships(admin_client):
    competition = admin_client.post('/competitions', json={'name':'Demo League','country':'Demo'}).json()
    response = admin_client.post('/clubs', json={'name':'Demo FC','competition_id':competition['id']})
    assert response.status_code == 201
    club = response.json()
    player = admin_client.post('/players', json={'name':'Demo Player','club':'Demo FC','club_id':club['id'],'age':22,'position':'CM','goals':0,'assists':0,'minutes_played':0})
    assert player.status_code == 201
    assert admin_client.get(f"/clubs/{club['id']}/players").json()['total'] == 1
    assert admin_client.get(f"/competitions/{competition['id']}/clubs").json()[0]['id'] == club['id']
    assert admin_client.delete(f"/clubs/{club['id']}").status_code == 409
    assert admin_client.delete(f"/competitions/{competition['id']}").status_code == 409


def test_legacy_player_club_strings_create_structured_relationships(admin_client):
    result = admin_client.post('/players', json={'name':'Demo Player','club':'Legacy Club','age':22,'position':'CM','goals':0,'assists':0,'minutes_played':0})
    assert result.status_code == 201
    with TestingSessionLocal() as db:
        player = db.get(Player, result.json()['id'])
        assert player.current_club.name == 'Legacy Club' and player.club_id is not None


def test_invalid_club_foreign_key_is_rejected(admin_client):
    response = admin_client.post('/players', json={'name':'Demo Player','club':'Missing','club_id':999,'age':22,'position':'CM','goals':0,'assists':0,'minutes_played':0})
    assert response.status_code == 409
    assert admin_client.post('/clubs', json={'name':'Demo','competition_id':999}).status_code == 404


def test_duplicate_entities_are_case_insensitive(admin_client):
    assert admin_client.post('/clubs', json={'name':'Demo FC'}).status_code == 201
    assert admin_client.post('/clubs', json={'name':'DEMO FC'}).status_code == 409
    assert admin_client.post('/competitions', json={'name':'League'}).status_code == 201
    assert admin_client.post('/competitions', json={'name':'LEAGUE'}).status_code == 409


@pytest.mark.parametrize('path', ['/clubs','/competitions'])
def test_entity_writes_require_admin_and_reads_are_public(client, path):
    assert client.get(path).status_code == 200
    assert client.post(path, json={'name':'Demo'}).status_code == 401


def test_club_name_change_updates_legacy_player_response(admin_client, seed_test_players):
    with TestingSessionLocal() as db:
        club_id = db.get(Player, 1).club_id
    assert admin_client.put(f'/clubs/{club_id}', json={'name':'Renamed Demo Club'}).status_code == 200
    assert admin_client.get('/players/1').json()['club'] == 'Renamed Demo Club'
