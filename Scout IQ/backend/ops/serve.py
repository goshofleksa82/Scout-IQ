"""Container entry point. Database migrations run separately, once per deployment."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import uvicorn
from app.core.operations import SafeJSONFormatter

config={'version':1,'disable_existing_loggers':False,'formatters':{'safe':{'()':SafeJSONFormatter}},'handlers':{'stdout':{'class':'logging.StreamHandler','formatter':'safe','stream':'ext://sys.stdout'}},'root':{'handlers':['stdout'],'level':'INFO'},'loggers':{'uvicorn':{'handlers':['stdout'],'level':'INFO','propagate':False},'uvicorn.error':{'level':'INFO'},'uvicorn.access':{'handlers':[],'propagate':False}}}
uvicorn.run('app.main:app',host='0.0.0.0',port=int(os.getenv('PORT','8001')),proxy_headers=True,forwarded_allow_ips=os.getenv('FORWARDED_ALLOW_IPS','127.0.0.1'),access_log=False,log_config=config)
