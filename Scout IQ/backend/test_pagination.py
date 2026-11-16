import pytest
from sqlalchemy import event
from conftest import test_engine


def test_first_and_last_player_pages(client, seed_test_players):
    first = client.get('/players?page=1&page_size=2').json()
    last = client.get('/players?page=2&page_size=2').json()
    assert [row['id'] for row in first['players']] == [1, 2]
    assert [row['id'] for row in last['players']] == [3]
    assert (first['total'], first['total_pages'], first['has_next'], first['has_previous']) == (3, 2, True, False)
    assert (last['has_next'], last['has_previous']) == (False, True)


def test_empty_pages_keep_correct_totals(client, seed_test_players):
    result = client.get('/players?page=5&page_size=2').json()
    assert result['players'] == [] and result['total'] == 3


def test_empty_database_pagination(client):
    result = client.get('/players').json()
    assert result['players'] == [] and result['total'] == 0 and result['total_pages'] == 0


@pytest.mark.parametrize('query', ['page=0', 'page=-1', 'page=x', 'page_size=0', 'page_size=101', 'page_size=-1'])
def test_pagination_validation(client, query):
    assert client.get('/players?' + query).status_code == 422


def test_pagination_is_applied_in_sql(client, seed_test_players):
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.upper())
    event.listen(test_engine, 'before_cursor_execute', capture)
    try:
        assert client.get('/players?page_size=1&page=2').json()['players'][0]['id'] == 2
    finally:
        event.remove(test_engine, 'before_cursor_execute', capture)
    assert any('LIMIT' in statement and 'OFFSET' in statement for statement in statements)
