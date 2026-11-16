"""Custom-format backups; guarded restores only into a separate empty scratch DB."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.urls import normalize_database_url


def pg_environment(url):
    env=dict(os.environ,PGHOST=url.host or 'localhost',PGPORT=str(url.port or 5432),PGUSER=url.username or '',PGPASSWORD=url.password or '',PGDATABASE=url.database or '')
    if url.query.get('sslmode'): env['PGSSLMODE']=url.query['sslmode']
    return env


def read_summary(conn,database):
    rows=conn.execute(text('SELECT id,name,age,position,club,goals,assists,minutes_played FROM players ORDER BY id')).all()
    counts={name:conn.scalar(text(f'SELECT count(*) FROM "{name}"')) for name in ('players','users','matches','player_match_stats','watchlists','scouting_reports','scouting_report_versions','audit_logs')}
    return {'database':database,'revision':conn.scalar(text('SELECT version_num FROM alembic_version')),'counts':counts,'original_player_fields_sha256':hashlib.sha256(repr(rows).encode()).hexdigest()}


def summary(url):
    engine=create_engine(url,connect_args={'connect_timeout':10})
    try:
        with engine.connect() as conn:
            conn.execute(text("SET TIME ZONE 'UTC'"))
            return read_summary(conn,url.database)
    finally: engine.dispose()


def restore(archive,target,pg_bin='',expected=None):
    source=make_url(normalize_database_url(os.environ['DATABASE_URL']));destination=make_url(normalize_database_url(target))
    if not destination.database or not destination.database.startswith('scoutiq_restore_'): raise RuntimeError('Restore database must be a separate scoutiq_restore_* scratch database')
    if (destination.host,destination.port,destination.database)==(source.host,source.port,source.database): raise RuntimeError('Source and restore targets must differ')
    engine=create_engine(destination)
    try:
        with engine.connect() as conn:
            if conn.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")): raise RuntimeError('Restore target must be empty; existing data will never be overwritten')
    finally: engine.dispose()
    executable=str(Path(pg_bin)/'pg_restore') if pg_bin else 'pg_restore'
    subprocess.run([executable,'--dbname',destination.database,'--no-owner','--no-acl','--exit-on-error','--single-transaction',str(archive)],env=pg_environment(destination),check=True,capture_output=True)
    result=summary(destination)
    if expected:
        for key in ('revision','counts','original_player_fields_sha256'):
            if result[key]!=expected[key]: raise RuntimeError('Backup restore verification failed: '+key)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--pg-bin',default='');parser.add_argument('--restore-into',action='store_true');args=parser.parse_args()
    if not os.environ.get('DATABASE_URL'): raise RuntimeError('DATABASE_URL is required; use an environment secret, never a command argument')
    url=make_url(normalize_database_url(os.environ['DATABASE_URL']));args.output.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');archive=args.output/f'scoutiq-{stamp}.dump'
    executable=str(Path(args.pg_bin)/'pg_dump') if args.pg_bin else 'pg_dump'
    # Export one consistent snapshot for both pg_dump and the verification manifest.
    engine=create_engine(url)
    try:
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            with conn.begin():
                conn.execute(text("SET TIME ZONE 'UTC'"))
                snapshot=conn.scalar(text('SELECT pg_export_snapshot()'))
                expected=read_summary(conn,url.database)
                subprocess.run([executable,'--format=custom','--no-owner','--no-acl','--snapshot',snapshot,'--file',str(archive)],env=pg_environment(url),check=True,capture_output=True)
    finally: engine.dispose()
    if os.name!='nt': archive.chmod(0o600)
    result={'created_at':datetime.now(timezone.utc).isoformat(),'backup':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source':expected}
    if args.restore_into:
        target=os.environ.get('RESTORE_DATABASE_URL')
        if not target: raise RuntimeError('RESTORE_DATABASE_URL must name an empty separate scratch database')
        result['restored']=restore(archive,target,args.pg_bin,expected)
    manifest=archive.with_suffix('.json');manifest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    if os.name!='nt': manifest.chmod(0o600)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try: main()
    except subprocess.CalledProcessError as error: raise SystemExit('PostgreSQL tool failed with exit code '+str(error.returncode)+'. Details are suppressed to protect connection secrets.') from None
