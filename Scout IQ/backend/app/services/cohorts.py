"""Season/position/source-compatible cohorts, aggregated in PostgreSQL."""
from collections import Counter
from sqlalchemy import func, select
from app.models import ImportBatch, Match, Player, PlayerMatchStats, Season
from app.services.advanced_metrics import metrics_from_totals
from app.services.entities import required
from app.services.statistics import METRICS

POSITION_GROUPS={
    'strikers':('ST','CF','FW'),
    'wingers':('LW','RW','LM','RM'),
    'midfielders':('CM','CAM','CDM','AM','DM'),
    'defenders':('CB','LB','RB','LWB','RWB'),
    'goalkeepers':('GK',),
}
POSITION_METRICS={
    'strikers':('goals_per_90','goal_contributions_per_90','assists_per_90','shots_per_90','goal_conversion_pct'),
    'wingers':('goal_contributions_per_90','assists_per_90','goals_per_90','shots_per_90','progressive_actions_per_90'),
    'midfielders':('assists_per_90','progressive_actions_per_90','tackles_per_90','pass_completion_pct','passes_completed_per_90'),
    'defenders':('tackles_per_90','pass_completion_pct','progressive_actions_per_90','passes_completed_per_90'),
    'goalkeepers':('pass_completion_pct','passes_completed_per_90'),
}


def position_group(position):
    return next((name for name,codes in POSITION_GROUPS.items() if position.upper() in codes),None)


def resolve_season(db,season_id=None,player_id=None):
    if season_id is not None: return required(db,Season,season_id).id
    query=select(Match.season_id).join(PlayerMatchStats,PlayerMatchStats.match_id==Match.id).where(Match.status=='finished')
    if player_id is not None: query=query.where(PlayerMatchStats.player_id==player_id)
    return db.scalar(query.order_by(Match.kickoff_at.desc(),Match.id.desc()).limit(1))


def cohort_players(db,season_id,min_minutes=450,group=None,data_source=None):
    if season_id is None: return []
    source=func.lower(func.coalesce(ImportBatch.source,'manual'))
    expressions=[Player.id,Player.name,Player.position,func.count(PlayerMatchStats.id),func.min(source),func.count(func.distinct(source)),func.max(PlayerMatchStats.updated_at)]
    for name in METRICS:
        column=getattr(PlayerMatchStats,name)
        expressions.extend((func.sum(column),func.count(column)))
    expressions.append(func.array_agg(func.distinct(source)))
    query=db.query(*expressions).join(PlayerMatchStats,PlayerMatchStats.player_id==Player.id).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id)
    query=query.filter(Match.status=='finished',Match.season_id==season_id)
    if data_source is not None: query=query.filter(source==data_source.strip().lower())
    if group is not None: query=query.filter(func.upper(Player.position).in_(POSITION_GROUPS[group]))
    query=query.group_by(Player.id,Player.name,Player.position).having(func.sum(PlayerMatchStats.minutes_played)>=min_minutes)
    results=[]
    for row in query.order_by(Player.id).all():
        count=row[3]; totals={}
        for index,name in enumerate(METRICS):
            value,available=row[7+2*index:9+2*index]
            totals[name]=value if available==count else None
        results.append({'player_id':row[0],'name':row[1],'position':row[2],'matches_recorded':count,
            'data_source':row[4] if row[5]==1 else None,'source_count':row[5],'source_names':sorted(row[-1]),
            'updated_at':row[6],'minutes_played':totals['minutes_played'],'totals':totals,
            'metrics':metrics_from_totals(totals)})
    return results


def percentile_map(values):
    """Mean-rank percentiles: ties share their average position; singleton=None."""
    counts=Counter(values); count=len(values); below=0; result={}
    for value in sorted(counts):
        equal=counts[value]
        result[value]={'rank':1+count-below-equal,'percentile':None if count<2 else round((below+(equal-1)/2)/(count-1)*100,2)}
        below+=equal
    return result
