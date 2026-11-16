"""Run a single reviewed upgrade with the owner-only migration connection."""
import os,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
if os.environ.get('MIGRATION_DATABASE_URL'): os.environ['DATABASE_URL']=os.environ['MIGRATION_DATABASE_URL']
from alembic import command
from alembic.config import Config
config=Config(str(root/'alembic.ini'));config.set_main_option('script_location',str(root/'migrations'))
command.upgrade(config,'head')
runpy.run_path(str(root/'ops/deploy_check.py'),run_name='__main__')
