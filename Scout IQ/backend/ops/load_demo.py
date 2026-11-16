"""Load the attributed historical demo once, atomically, into an empty demo DB."""
import argparse,hashlib,json,os,re,sys
from datetime import date
from pathlib import Path
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.urls import normalize_database_url
from app.core.auditing import set_actor
from app.models import Club,Competition,ImportBatch,ImportIdentity,Match,MatchParticipant,Membership,Player,PlayerMatchStats,Season,User
from app.schemas import PlayerCreate
from app.schemas.matches import MatchCreate
from app.schemas.statistics import StatsValues

DEMO_DIR=Path(__file__).resolve().parents[1]/'demo'


def load_demo(database_url,actor_username,schema=None):
    url=make_url(normalize_database_url(database_url))
    test_schema=url.database=='scoutiq_test' and schema and re.fullmatch(r'scoutiq_demo_[a-z0-9_]+',schema)
    if not (url.database and url.database.startswith('scoutiq_demo')) and not test_schema:
        raise RuntimeError('Demo loading requires a separate empty scoutiq_demo* database; development and production targets are refused')
    if schema and not test_schema: raise RuntimeError('Schema overrides are restricted to named disposable test schemas')
    if test_schema: url=url.update_query_dict({'options':'-csearch_path='+schema+',public'})
    raw=(DEMO_DIR/'world-cup-2018.json').read_bytes();manifest=json.loads((DEMO_DIR/'manifest.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=manifest['dataset_sha256']: raise RuntimeError('Demo dataset checksum does not match its manifest')
    dataset=json.loads(raw)
    if dataset['license']!='CC BY 4.0': raise RuntimeError('Unexpected demonstration data rights')
    engine=create_engine(url,connect_args={'connect_timeout':10})
    try:
        with Session(engine,autoflush=False) as db:
            # An advisory lock serializes competing loaders, including the empty
            # target check. All football rows and provenance share one transaction.
            db.execute(text('SELECT pg_advisory_xact_lock(705041850)'))
            if db.scalar(select(Player.id).limit(1)) is not None or db.scalar(select(Match.id).limit(1)) is not None:
                raise RuntimeError('Demo target must have no player or match data. Existing data is never overwritten')
            actor=db.scalar(select(User).where(User.username==actor_username,User.role=='admin',User.is_active.is_(True)))
            if actor is None: raise RuntimeError('Create an administrator through the local operator bootstrap first')
            set_actor(db,actor.id)
            report={'demo':True,'age_as_of':dataset['age_as_of'],'observation_window':dataset['observation_window'],'team_context':dataset['team_context'],'position_context':dataset['position_context'],'dataset_sha256':manifest['dataset_sha256'],'omitted_samples':dataset['omitted'],'license_url':dataset['license_url'],'citation':dataset['citation'],'collection':dataset['collection']}
            batch=ImportBatch(user_id=actor.id,kind='historical-demo',source=dataset['source'],rights_basis='CC BY 4.0; Pappalardo et al. (2019). https://doi.org/10.1038/s41597-019-0247-7',status='complete',report=report);competition=Competition(**dataset['competition']);season=Season(name=dataset['season']['name'],starts_on=date.fromisoformat(dataset['season']['starts_on']),ends_on=date.fromisoformat(dataset['season']['ends_on']))
            db.add_all([batch,competition,season]);db.flush()
            clubs={}
            for source in dataset['clubs']:
                row=Club(name=source['name'],country=source['country'],competition_id=competition.id);db.add(row);db.flush();clubs[int(source['external_id'])]=row
            def identity(kind,external_id,row_id,values):
                db.add(ImportIdentity(source=dataset['source'].casefold(),kind=kind,external_id=str(external_id),record_id=row_id,fingerprint=hashlib.sha256(json.dumps(values,sort_keys=True,default=str).encode()).hexdigest(),batch_id=batch.id))
            players={}
            for source in dataset['players']:
                values={k:source[k] for k in ['name','age','position','club','goals','assists','minutes_played']};values['club_id']=clubs[source['team_id']].id
                values=PlayerCreate.model_validate(values).model_dump();row=Player(**values,import_batch_id=batch.id);db.add(row);db.flush();players[int(source['external_id'])]=row
                identity('players',source['external_id'],row.id,values)
                # This interval represents the demo tournament window only; it
                # is not a claimed professional transfer or national-team debut.
                db.add(Membership(player_id=row.id,club_id=row.club_id,season_id=season.id,joined_on=season.starts_on))
            matches={}
            for source in dataset['matches']:
                values=MatchCreate.model_validate({'home_club_id':clubs[source['home_team_id']].id,'away_club_id':clubs[source['away_team_id']].id,'competition_id':competition.id,'season_id':season.id,'kickoff_at':source['kickoff_at'],'duration_minutes':source['duration_minutes'],'status':'finished'}).model_dump()
                row=Match(**values,import_batch_id=batch.id);db.add(row);db.flush();matches[int(source['external_id'])]=row;identity('matches',source['external_id'],row.id,values)
            for source in dataset['statistics']:
                player=players[source['player_id']];match=matches[source['match_id']]
                if player.club_id not in [match.home_club_id,match.away_club_id]: raise RuntimeError('Demo roster is inconsistent')
                db.add(MatchParticipant(match_id=match.id,player_id=player.id,club_id=player.club_id))
            db.flush()
            for source in dataset['statistics']:
                values=StatsValues.model_validate({k:source[k] for k in StatsValues.model_fields}).model_dump();player=players[source['player_id']];match=matches[source['match_id']]
                row=PlayerMatchStats(player_id=player.id,match_id=match.id,import_batch_id=batch.id,**values);db.add(row);db.flush();identity('player-stats',str(source['match_id'])+':'+str(source['player_id']),row.id,values)
            batch.report={**report,'inserted':len(players)+len(matches)+len(dataset['statistics']),'counts':manifest['counts']}
            db.commit();return manifest['counts']
    finally: engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--actor',required=True,help='Existing administrator username in the new demo database');args=parser.parse_args()
    if not os.environ.get('DATABASE_URL'): raise SystemExit('Set the isolated demo DATABASE_URL in your environment, never in command arguments')
    print(json.dumps(load_demo(os.environ['DATABASE_URL'],args.actor),indent=2))
