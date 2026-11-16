"""Atomic CSV ingestion with stable source identities and explicit provenance."""
import csv
import hashlib
import io
import json
from datetime import timezone
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, insert, select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models import Club, Competition, ImportBatch, ImportIdentity, Match, MatchEvent, MatchParticipant, Player, PlayerMatchStats, Season
from app.schemas.imports import ImportPlayer, ImportMatch, ImportStatistics

REGISTRY={'players':(ImportPlayer,Player),'matches':(ImportMatch,Match),'player-stats':(ImportStatistics,PlayerMatchStats)}


def parse_csv(raw, schema):
    try: content=raw.decode('utf-8-sig')
    except UnicodeDecodeError: raise HTTPException(status_code=400,detail='CSV must be UTF-8 encoded') from None
    reader=csv.DictReader(io.StringIO(content),strict=True)
    headers=reader.fieldnames or []
    required={name for name,field in schema.model_fields.items() if field.is_required()}
    if not headers or len(set(headers))!=len(headers) or not required.issubset(headers) or set(headers)-set(schema.model_fields):
        raise HTTPException(status_code=400,detail='CSV headers must be unique supported fields and include all required columns')
    valid=[]; errors=[]; total=0
    try:
        for row in reader:
            total+=1
            if total>1000: raise HTTPException(status_code=413,detail='CSV is limited to 1000 records per batch')
            line=reader.line_num
            if None in row or any(value is None for value in row.values()):
                errors.append({'line':line,'message':'CSV row has a different number of columns from its header'}); continue
            values={key:(None if value.strip()=='' else value.strip()) for key,value in row.items()}
            try:
                parsed=schema.model_validate(values)
                fingerprint=hashlib.sha256(json.dumps(parsed.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()
                valid.append((line,parsed,fingerprint))
            except ValidationError as exc:
                errors.append({'line':line,'message':'; '.join('.'.join(map(str,e['loc']))+': '+e['msg'] for e in exc.errors())})
    except csv.Error:
        raise HTTPException(status_code=400,detail='Malformed CSV quoting') from None
    if total==0: raise HTTPException(status_code=400,detail='CSV contains no records')
    return total,valid,errors


def _validate_references(db,kind,records):
    errors=[]
    if kind=='players':
        ids={item.club_id for _,item,_ in records if item.club_id is not None}
        clubs={row.id:row for row in db.scalars(select(Club).where(Club.id.in_(ids))).all()} if ids else {}
        for line,item,_ in records:
            if item.club_id is not None and (item.club_id not in clubs or clubs[item.club_id].name.casefold()!=item.club.casefold()):
                errors.append({'line':line,'message':'club_id is missing or does not match the club name'})
    elif kind=='matches':
        club_ids={value for _,item,_ in records for value in (item.home_club_id,item.away_club_id)}
        clubs=set(db.scalars(select(Club.id).where(Club.id.in_(club_ids))))
        competitions=set(db.scalars(select(Competition.id)))
        seasons={row.id:row for row in db.scalars(select(Season))}
        for line,item,_ in records:
            season=seasons.get(item.season_id)
            if item.home_club_id not in clubs or item.away_club_id not in clubs or item.competition_id not in competitions or season is None:
                errors.append({'line':line,'message':'Unknown club, competition, or season'})
            elif not season.starts_on<=item.kickoff_at.astimezone(timezone.utc).date()<=season.ends_on:
                errors.append({'line':line,'message':'Match date is outside its season'})
    else:
        pairs={(item.match_id,item.player_id) for _,item,_ in records}
        participants=set(db.execute(select(MatchParticipant.match_id,MatchParticipant.player_id).where(tuple_(MatchParticipant.match_id,MatchParticipant.player_id).in_(pairs))).all())
        matches={row.id:row for row in db.scalars(select(Match).where(Match.id.in_({pair[0] for pair in pairs})))}
        counts={(match,player,kind):count for match,player,kind,count in db.execute(select(MatchEvent.match_id,MatchEvent.player_id,MatchEvent.event_type,func.count()).where(tuple_(MatchEvent.match_id,MatchEvent.player_id).in_(pairs)).group_by(MatchEvent.match_id,MatchEvent.player_id,MatchEvent.event_type))}
        for line,item,_ in records:
            match=matches.get(item.match_id)
            if (item.match_id,item.player_id) not in participants or match is None:
                errors.append({'line':line,'message':'Player is not a registered match participant'})
            elif match.status=='scheduled' or item.minutes_played>match.duration_minutes+30:
                errors.append({'line':line,'message':'Invalid match status or playing time'})
            elif item.goals<counts.get((item.match_id,item.player_id,'goal'),0) or item.assists<counts.get((item.match_id,item.player_id,'assist'),0):
                errors.append({'line':line,'message':'Statistics contradict recorded match events'})
    return errors


def _bulk_insert(db,kind,model,records,batch_id):
    values=[item.model_dump(exclude={'external_id'}) for _,item,_ in records]
    if kind=='players':
        names={row['club'].casefold():row['club'] for row in values if row.get('club_id') is None}
        if names:
            db.execute(pg_insert(Club).values([{'name':name} for name in names.values()]).on_conflict_do_nothing())
            clubs={row.name.casefold():row.id for row in db.scalars(select(Club).where(Club.country.is_(None),func.lower(Club.name).in_(names)))}
            for row in values:
                if row.get('club_id') is None: row['club_id']=clubs[row['club'].casefold()]
    for row in values: row['import_batch_id']=batch_id
    return list(db.scalars(insert(model).returning(model.id,sort_by_parameter_order=True),values))


def _write_identities(db,kind,source,records,ids,batch_id):
    db.execute(insert(ImportIdentity),[{'source':source,'kind':kind,'external_id':item.external_id,'record_id':record_id,'fingerprint':fingerprint,'batch_id':batch_id} for (_,item,fingerprint),record_id in zip(records,ids)])


def _report(db,batch,report,status):
    batch.status=status; batch.report=report
    db.add(batch); db.flush()
    result={'batch_id':batch.id,'source':batch.source,'rights_basis':batch.rights_basis,'status':status,**report}
    db.commit()
    return result


def import_csv(db,user_id,kind,source,rights_basis,raw):
    schema,model=REGISTRY[kind]
    source=source.strip(); rights_basis=rights_basis.strip()
    if not source or not rights_basis: raise HTTPException(status_code=422,detail='Source and rights basis cannot be blank')
    total,records,errors=parse_csv(raw,schema)
    key=source.casefold()
    external_ids=[item.external_id for _,item,_ in records]
    known={row.external_id:row for row in db.scalars(select(ImportIdentity).where(ImportIdentity.source==key,ImportIdentity.kind==kind,ImportIdentity.external_id.in_(external_ids)))}
    targets=set(db.scalars(select(model.id).where(model.id.in_([row.record_id for row in known.values()])))) if known else set()
    seen={}; pending=[]; skipped=0
    for line,item,fingerprint in records:
        existing=known.get(item.external_id)
        previous=seen.get(item.external_id)
        if existing is not None and (existing.fingerprint!=fingerprint or existing.record_id not in targets):
            errors.append({'line':line,'message':'External ID changed contents or its imported record was deleted; no automatic overwrite is allowed'})
        elif previous is not None and previous!=fingerprint:
            errors.append({'line':line,'message':'Conflicting duplicate external ID within the CSV'})
        elif existing is not None or previous is not None: skipped+=1
        else: pending.append((line,item,fingerprint))
        seen[item.external_id]=fingerprint
    errors.extend(_validate_references(db,kind,pending))
    batch=ImportBatch(user_id=user_id,kind=kind,source=source,rights_basis=rights_basis,status='rejected')
    report={'total_rows':total,'inserted':0,'skipped':skipped,'failed':len(errors),'errors':errors[:100]}
    if errors: return _report(db,batch,report,'rejected'),422
    try:
        db.add(batch); db.flush()
        if pending:
            ids=_bulk_insert(db,kind,model,pending,batch.id)
            _write_identities(db,kind,key,pending,ids,batch.id)
        report['inserted']=len(pending)
        return _report(db,batch,report,'complete'),200
    except SQLAlchemyError:
        db.rollback()
        failed=ImportBatch(user_id=user_id,kind=kind,source=source,rights_basis=rights_basis,status='failed')
        report.update(inserted=0,failed=len(pending),errors=[{'line':None,'message':'Database conflict or invalid record; the entire import was rolled back'}])
        return _report(db,failed,report,'failed'),409
