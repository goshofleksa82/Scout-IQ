from unittest.mock import MagicMock
from sqlalchemy.exc import SQLAlchemyError
import pytest
from conftest import TestingSessionLocal
from models import Club, ImportIdentity, Player
from test_matches import match_data

PARAMS={'source':'Synthetic fixture','rights_basis':'Original software test fixture','rights_confirmed':True}
CSV='external_id,name,age,position,club,goals,assists,minutes_played\ndemo-1,Synthetic Import A,22,CM,Synthetic FC,0,0,0\ndemo-2,Synthetic Import B,23,ST,Synthetic FC,1,0,90\n'


def upload(client,csv=CSV,kind='players',params=None):
    return client.post('/imports/'+kind,params=params or PARAMS,content=csv.encode(),headers={'Content-Type':'text/csv'})


def test_bulk_import_and_idempotent_reimport(admin_client):
    first=upload(admin_client)
    assert first.status_code==200 and first.json()['inserted']==2
    second=upload(admin_client)
    assert second.status_code==200 and second.json()['inserted']==0 and second.json()['skipped']==2
    with TestingSessionLocal() as db:
        assert db.query(Player).count()==2 and db.query(Club).count()==1
        assert all(player.import_batch_id==first.json()['batch_id'] for player in db.query(Player))
    assert admin_client.get('/imports/batches/'+str(first.json()['batch_id'])).json()['source']==PARAMS['source']


def test_invalid_row_rejects_entire_dataset(admin_client):
    response=upload(admin_client,CSV.replace('demo-2,Synthetic Import B,23','demo-2,Synthetic Import B,-1'))
    assert response.status_code==422 and response.json()['inserted']==0
    assert response.json()['errors'][0]['line']==3
    with TestingSessionLocal() as db: assert db.query(Player).count()==0


def test_conflicting_external_ids_never_overwrite(admin_client):
    assert upload(admin_client).status_code==200
    response=upload(admin_client,CSV.replace('Synthetic Import A','Changed Name'))
    assert response.status_code==422
    with TestingSessionLocal() as db: assert db.query(Player).filter(Player.name=='Synthetic Import A').count()==1


def test_database_failure_rolls_back_rows_clubs_and_identities(admin_client,monkeypatch):
    from app.services import imports
    monkeypatch.setattr(imports,'_write_identities',MagicMock(side_effect=SQLAlchemyError('private-database-detail')))
    response=upload(admin_client)
    assert response.status_code==409 and response.json()['inserted']==0
    assert 'private-database-detail' not in response.text
    with TestingSessionLocal() as db:
        assert db.query(Player).count()==0 and db.query(Club).count()==0 and db.query(ImportIdentity).count()==0


@pytest.mark.parametrize('csv',['name,age\nExample,22','external_id,name,name\na,b,c',''])
def test_malformed_csv_headers(admin_client,csv): assert upload(admin_client,csv).status_code==400


def test_import_requires_admin_and_rights_confirmation(client,admin_client):
    assert upload(admin_client,params={**PARAMS,'rights_confirmed':False}).status_code==400
    admin_client.headers.pop('Authorization')
    assert upload(client).status_code==401


def test_match_and_player_stats_imports(admin_client,match_data):
    payload=match_data['payload']
    csv='external_id,home_club_id,away_club_id,competition_id,season_id,kickoff_at,status\nmatch-demo,'+','.join(str(payload[key]) for key in ('home_club_id','away_club_id','competition_id','season_id','kickoff_at','status'))+'\n'
    assert upload(admin_client,csv,kind='matches').json()['inserted']==1
    csv=f"external_id,player_id,match_id,minutes_played,goals,assists,shots\nstats-demo,{match_data['players'][0]},{match_data['match']},90,1,0,2\n"
    result=upload(admin_client,csv,kind='player-stats')
    assert result.status_code==200 and result.json()['inserted']==1


def test_import_match_season_uses_utc_date(admin_client,match_data):
    payload={**match_data['payload'],'kickoff_at':'2026-01-01T00:30:00+02:00'}
    csv='external_id,home_club_id,away_club_id,competition_id,season_id,kickoff_at,status\ntimezone-demo,'+','.join(str(payload[key]) for key in ('home_club_id','away_club_id','competition_id','season_id','kickoff_at','status'))+'\n'
    assert upload(admin_client,csv,kind='matches').status_code==422
