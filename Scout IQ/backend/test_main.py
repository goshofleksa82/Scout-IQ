
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# Test 1: Home endpoint
def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to ScoutIQ"


# Test 2: Get all players
def test_get_all_players():
    response = client.get("/players")

    assert response.status_code == 200
    assert len(response.json()["players"]) == 5


# Test 3: Get player by ID
def test_get_player_by_id():
    response = client.get("/players/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Erling Haaland"


# Test 4: Player not found
def test_player_not_found():
    response = client.get("/players/999")

    assert response.status_code == 404


# Test 5: Sort players by goals
def test_sort_players():
    response = client.get("/players/sort?sort_by=goals&order=desc")

    assert response.status_code == 200

    players = response.json()
    goals = [player["goals"] for player in players]

    assert goals == sorted(goals, reverse=True)


# Test 6: Compare same player
def test_compare_same_player():
    response = client.get("/players/compare?player1=1&player2=1")

    assert response.status_code == 400


# Test 7: Player rankings
def test_player_rankings():
    response = client.get("/players/rankings?metric=goals_per_90")

    assert response.status_code == 200

    rankings = response.json()["rankings"]
    values = [player["value"] for player in rankings]

    assert values == sorted(values, reverse=True)
