"""Derive a small attributed historical demo from verified CC BY 4.0 sources."""
from pathlib import Path
from datetime import date,datetime,timezone
from collections import defaultdict,Counter
import hashlib,json,re,sys,zipfile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path,required=True);args=parser.parse_args()
from app.schemas.statistics import StatsValues
source=args.source_dir;out=ROOT;out.mkdir(exist_ok=True)
with zipfile.ZipFile(source/'matches.zip') as z: matches=json.loads(z.read('matches_World_Cup.json'))
with zipfile.ZipFile(source/'events.zip') as z: events=json.loads(z.read('events_World_Cup.json'))
players={p['wyId']:p for p in json.loads((source/'players.json').read_text())}
teams={t['wyId']:t for t in json.loads((source/'teams.json').read_text())}
selected={key for key,t in teams.items() if t['name'] in ['France','Croatia']}
assert len(selected)==2
matches=sorted([m for m in matches if selected.intersection(map(int,m['teamsData']))],key=lambda m:m['dateutc'])
assert len(matches)==13
events_by_pair=defaultdict(list)
for e in events:
    if e['matchId'] in {m['wyId'] for m in matches} and e['teamId'] in selected and e['matchPeriod']!='P': events_by_pair[e['matchId'],e['playerId']].append(e)
print('Source periods',dict(Counter(e['matchPeriod'] for e in events)),flush=True)
samples=[];omitted=[];roster={};validation=[]
def clean_name(value): return re.sub(r'\\u([0-9a-fA-F]{4})',lambda m:chr(int(m[1],16)),value)
for match in matches:
    duration=120 if match['duration'] in ['Penalties','ExtraTime'] else 90
    assert match['duration'] in ['Regular','Penalties','ExtraTime']
    for team_key,side in match['teamsData'].items():
        tid=int(team_key)
        if tid not in selected:continue
        formation=side['formation'];subs=formation.get('substitutions') or []
        starters={p['playerId'] for p in formation['lineup']}
        appearances={**{p['playerId']:p for p in formation['lineup']},**{p['playerId']:p for p in formation['bench'] if p['playerId'] in {s['playerIn'] for s in subs}}}
        for pid,appearance in appearances.items():
            start=0 if pid in starters else next(s['minute'] for s in subs if s['playerIn']==pid)
            end=next((s['minute'] for s in subs if s['playerOut']==pid),duration)
            minutes=max(0,min(duration,end)-min(duration,start))
            feed=events_by_pair[match['wyId'],pid]
            assert not any({1701,1703}.intersection(t['id'] for t in e['tags']) for e in feed),'Red cards require a separate minute reconstruction'
            shots=[e for e in feed if e['eventName']=='Shot' or (e['eventName']=='Free Kick' and e['subEventName'] in ['Penalty','Free kick shot'])]
            goals=sum(101 in {t['id'] for t in e['tags']} and 102 not in {t['id'] for t in e['tags']} for e in shots)
            known_goals=appearance.get('goals')
            if str(known_goals).isdigit() and int(known_goals)!=goals: validation.append({'match':match['wyId'],'player':pid,'source_goals':known_goals,'derived_goals':goals})
            assists=appearance.get('assists')
            if not str(assists).isdigit():
                omitted.append({'match':match['wyId'],'player':pid,'reason':'Unknown recorded assists'});continue
            passes=[e for e in feed if e['eventName']=='Pass']
            stats={'minutes_played':minutes,'goals':goals,'assists':int(assists),'shots':len(shots),'passes_attempted':len(passes),'passes_completed':sum(1801 in {t['id'] for t in e['tags']} for e in passes),'tackles':None,'progressive_passes':None,'progressive_carries':None}
            if minutes==0:
                omitted.append({'match':match['wyId'],'player':pid,'reason':'Late substitution has no reconstructable regulation minutes'});continue
            StatsValues.model_validate(stats)
            samples.append({'match_id':match['wyId'],'player_id':pid,'team_id':tid,**stats});roster[pid]=tid
assert not validation,validation
assert all(e['matchPeriod']!='P' for values in events_by_pair.values() for e in values)
totals=defaultdict(lambda:{'goals':0,'assists':0,'minutes_played':0})
for s in samples:
    for key in totals[s['player_id']]:totals[s['player_id']][key]+=s[key]
as_of=date(2018,7,15)
player_rows=[]
for pid,tid in sorted(roster.items()):
    p=players[pid];born=date.fromisoformat(p['birthDate']);age=as_of.year-born.year-((as_of.month,as_of.day)<(born.month,born.day))
    role={'Forward':'FW','Midfielder':'CM','Defender':'CB','Goalkeeper':'GK'}[p['role']['name']]
    player_rows.append({'external_id':str(pid),'name':clean_name(' '.join(filter(None,[p['firstName'],p['lastName']]))),'age':age,'position':role,'club':teams[tid]['name'],'team_id':tid,**totals[pid]})
club_ids={int(key) for m in matches for key in m['teamsData']}
match_rows=[]
for m in matches:
    home=next(int(k) for k,v in m['teamsData'].items() if v['side']=='home');away=next(int(k) for k,v in m['teamsData'].items() if v['side']=='away')
    match_rows.append({'external_id':str(m['wyId']),'home_team_id':home,'away_team_id':away,'kickoff_at':datetime.fromisoformat(m['dateutc']).replace(tzinfo=timezone.utc).isoformat(),'duration_minutes':120 if m['duration'] in ['Penalties','ExtraTime'] else 90,'status':'finished','source_label':clean_name(m['label'])})
dataset={'schema_version':1,'source':'Wyscout open dataset · World Cup 2018','license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','citation':'Pappalardo et al. (2019), Scientific Data 6, 236. https://doi.org/10.1038/s41597-019-0247-7','collection':'https://doi.org/10.6084/m9.figshare.c.4415000','age_as_of':as_of.isoformat(),'observation_window':'Selected France and Croatia appearances at the 2018 World Cup; regulation and extra time excluding added time and shoot-outs. Late-substitution samples with zero reconstructable regulation minutes are omitted.','team_context':'National teams at the 2018 tournament, not current professional clubs.','position_context':'Broad source roles: Forward→FW, Midfielder→CM, Defender→CB, Goalkeeper→GK. No finer tactical role is inferred.','competition':{'name':'World Cup 2018 · historical demo','country':'Russia'},'season':{'name':'World Cup 2018 demo','starts_on':'2018-06-14','ends_on':'2018-07-15'},'clubs':[{'external_id':str(tid),'name':teams[tid]['name'],'country':teams[tid].get('area',{}).get('name')} for tid in sorted(club_ids)],'players':player_rows,'matches':match_rows,'statistics':samples,'omitted':omitted}
raw=(json.dumps(dataset,ensure_ascii=False,indent=2)+'\n').encode('utf-8');(out/'world-cup-2018.json').write_bytes(raw)
manifest={'dataset_sha256':hashlib.sha256(raw).hexdigest(),'counts':{k:len(dataset[k]) for k in ['clubs','players','matches','statistics','omitted']},'validation':{'known_source_goal_fields_matched':True,'shootouts_excluded':True,'all_statistics_pass_schema_validation':True},'source_files':[]}
for article in [7765196,7765310,7770599,7770422]:
    meta=json.loads((source/(str(article)+'-metadata.json')).read_text());assert meta['license']['name']=='CC BY 4.0'
    for f in meta['files']:manifest['source_files'].append({'article_doi':meta['doi'],'name':f['name'],'download_url':f['download_url'],'md5':hashlib.md5((source/f['name']).read_bytes()).hexdigest()})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2),flush=True)
