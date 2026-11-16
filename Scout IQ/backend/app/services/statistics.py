from fastapi import HTTPException
from sqlalchemy import case, func, select
from app.models import ImportBatch, Match, MatchEvent, MatchParticipant, Player, PlayerMatchStats, Season
from app.services.entities import required
from app.services.matches import commit

METRICS = ('minutes_played','goals','assists','shots','passes_attempted','passes_completed','tackles','progressive_passes','progressive_carries')


def save_statistics(db, match_id, player_id, data, replace=False):
    match = required(db,Match,match_id)
    if db.get(MatchParticipant,(match_id,player_id)) is None:
        raise HTTPException(status_code=400,detail='Player is not a registered participant')
    if match.status == 'scheduled': raise HTTPException(status_code=400,detail='Scheduled matches cannot have recorded statistics')
    if data.minutes_played > match.duration_minutes+30: raise HTTPException(status_code=400,detail='Playing time exceeds match duration and stoppage allowance')
    for kind, value in (('goal',data.goals),('assist',data.assists)):
        recorded = db.scalar(select(func.count()).select_from(MatchEvent).where(MatchEvent.match_id==match_id,MatchEvent.player_id==player_id,MatchEvent.event_type==kind))
        if value < recorded: raise HTTPException(status_code=400,detail='Statistics cannot be lower than recorded match events')
    existing = db.scalar(select(PlayerMatchStats).where(PlayerMatchStats.match_id==match_id,PlayerMatchStats.player_id==player_id))
    if replace and existing is None: raise HTTPException(status_code=404,detail='Player match statistics not found')
    if not replace and existing is not None: raise HTTPException(status_code=409,detail='Player match statistics already recorded')
    values = data.model_dump(exclude={'player_id'})
    row = existing or PlayerMatchStats(match_id=match_id,player_id=player_id)
    for name,value in values.items(): setattr(row,name,value)
    return commit(db,row)


def aggregate_statistics(db, player_id, season_id=None, data_source=None):
    required(db,Player,player_id)
    if season_id is not None: required(db,Season,season_id)
    expressions = [func.count(PlayerMatchStats.id),func.count(case((PlayerMatchStats.minutes_played>0,1)))]
    for name in METRICS:
        column=getattr(PlayerMatchStats,name)
        expressions.extend((func.sum(column),func.count(column)))
    query=db.query(*expressions).join(Match,Match.id==PlayerMatchStats.match_id).filter(PlayerMatchStats.player_id==player_id,Match.status=='finished')
    if season_id is not None: query=query.filter(Match.season_id==season_id)
    source=func.lower(func.coalesce(ImportBatch.source,'manual'))
    if data_source is not None:
        query=query.outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id).filter(source==data_source.strip().lower())
    row=query.one(); count=row[0]
    sources=db.query(func.distinct(func.lower(func.coalesce(ImportBatch.source,'manual')))).select_from(PlayerMatchStats).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id).filter(PlayerMatchStats.player_id==player_id,Match.status=='finished')
    if season_id is not None: sources=sources.filter(Match.season_id==season_id)
    if data_source is not None: sources=sources.filter(source==data_source.strip().lower())
    source_names=sorted(value[0] for value in sources.all())
    totals={}; coverage={}
    for index,name in enumerate(METRICS):
        value,available=row[2+index*2:4+index*2]
        totals[name]=value if count>0 and available==count else None
        coverage[name]={'available':available,'total':count}
    updated=db.query(func.max(PlayerMatchStats.updated_at)).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id).filter(PlayerMatchStats.player_id==player_id,Match.status=='finished')
    if season_id is not None: updated=updated.filter(Match.season_id==season_id)
    if data_source is not None: updated=updated.filter(source==data_source.strip().lower())
    return {'player_id':player_id,'season_id':season_id,'matches_recorded':count,'matches_played':row[1],'updated_at':updated.scalar(),
            'totals':totals,'metric_coverage':coverage,'source':'player_match_stats','data_sources':source_names,
            'data_status':'no_data' if count==0 else ('partial' if any(v is None for v in totals.values()) else 'available')}
