import pytest


def test_combined_search_filters_and_case(client, seed_test_players):
    result = client.get('/players/search', params={'name': 'HAAL', 'club': 'MANCHESTER CITY', 'position': 'st', 'min_goals': 20, 'max_age': 26, 'min_minutes': 1800}).json()
    assert result['total'] == 1 and result['players'][0]['id'] == 1
    assert client.get('/players/search?min_goals=21').json()['total'] == 0


def test_search_sort_and_pagination(client, seed_test_players):
    result = client.get('/players/search?sort_by=assists&order=desc&page_size=1&page=2').json()
    assert result['total'] == 3 and result['players'][0]['id'] == 3


@pytest.mark.parametrize('query', ['min_age=30&max_age=20', 'min_goals=-1', 'min_assists=5&max_assists=2', 'min_minutes=5&max_minutes=2', 'sort_by=password', 'order=random', 'page_size=101', 'name=%20%20', 'unexpected=1'])
def test_invalid_search_queries(client, query):
    assert client.get('/players/search?' + query).status_code == 422


@pytest.mark.parametrize('query', ['name=%25', 'name=_', "name=' OR 1=1 --"])
def test_name_search_treats_wildcards_and_sql_as_literal(client, seed_test_players, query):
    response = client.get('/players/search?' + query)
    assert response.status_code == 200
    assert response.json()['total'] == 0


def test_search_bounds_are_inclusive(client, seed_test_players):
    result = client.get('/players/search?min_goals=18&max_goals=18&min_assists=9&max_assists=9').json()
    assert [row['id'] for row in result['players']] == [2]
