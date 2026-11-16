"""Bounded aggregate monitoring without paths, query strings, bodies or identities."""
from collections import Counter
from datetime import datetime,timezone
import json,logging,time
from threading import Lock
from uuid import uuid4
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

logger=logging.getLogger('scoutiq.http')
_lock=Lock();_counts=Counter();_durations=Counter();_started=datetime.now(timezone.utc).isoformat()


class SafeJSONFormatter(logging.Formatter):
    def format(self,record):
        payload={'time':datetime.now(timezone.utc).isoformat(),'level':record.levelname,'logger':record.name,'message':record.getMessage()[:500]}
        for name in ('request_id','method','route','status','duration_ms'):
            if hasattr(record,name): payload[name]=getattr(record,name)
        # Tracebacks can contain SQL parameters and are not emitted to shared logs.
        if record.exc_info: payload['error_type']=record.exc_info[0].__name__
        return json.dumps(payload)


def snapshot():
    with _lock:
        return {'started_at':_started,'scope':'This process only; counters reset on restart. No user identifiers or query strings are collected.','requests':[{'method':key[0],'route':key[1],'status':key[2],'count':value,'total_duration_ms':round(_durations[key],2)} for key,value in sorted(_counts.items())]}


class OperationalMiddleware:
    def __init__(self,app,hosted=False): self.app=app;self.hosted=hosted
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        request_id=uuid4().hex;started=time.perf_counter();status=500;begun=False
        async def output(message):
            nonlocal status,begun
            if message['type']=='http.response.start':
                status=message['status'];begun=True;headers=MutableHeaders(scope=message)
                headers['X-Request-ID']=request_id;headers['X-Content-Type-Options']='nosniff';headers['Referrer-Policy']='no-referrer';headers['Cache-Control']='no-store'
                if self.hosted: headers['Strict-Transport-Security']='max-age=31536000'
            await send(message)
        try: await self.app(scope,receive,output)
        except Exception as error:
            logger.error('Unhandled request failure',extra={'request_id':request_id,'status':500})
            if begun: raise
            await JSONResponse({'detail':'Service temporarily unavailable'},status_code=500)(scope,receive,output)
        finally:
            route=getattr(scope.get('route'),'path','unmatched');method=scope.get('method','UNKNOWN');duration=(time.perf_counter()-started)*1000;key=(method,route,status)
            with _lock:
                # Route templates are fixed; unknown URLs share one counter.
                if len(_counts)<2000 or key in _counts: _counts[key]+=1;_durations[key]+=duration
            logger.info('HTTP request',extra={'request_id':request_id,'method':method,'route':route,'status':status,'duration_ms':round(duration,2)})
