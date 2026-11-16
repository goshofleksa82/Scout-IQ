"""Observed rolling rates and explicitly exploratory permutation comparisons."""
from itertools import combinations
from math import comb
from random import Random
from fastapi import HTTPException
from sqlalchemy import func
from app.models import ImportBatch, Match, Player, PlayerMatchStats, Season
from app.services.advanced_metrics import METRIC_DEFINITIONS, metrics_from_totals
from app.services.cohorts import resolve_season
from app.services.entities import required
from app.services.statistics import METRICS


def window_metric(rows,metric):
    totals={name:None if any(row.get(name) is None for row in rows) else sum(row[name] for row in rows) for name in METRICS}
    return metrics_from_totals(totals)[metric] if rows else None


def rolling_values(rows,metric,window,min_samples):
    return [window_metric(rows[max(0,index-window+1):index+1],metric) if min(index+1,window)>=min_samples else None for index in range(len(rows))]


def permutation_comparison(historical,recent,metric):
    pooled=historical+recent; count=len(historical); size=len(pooled)
    observed=abs(window_metric(recent,metric)-window_metric(historical,metric))
    exact=comb(size,count)<=5000
    rng=Random(0)
    partitions=combinations(range(size),count) if exact else (rng.sample(range(size),count) for _ in range(2000))
    extreme=total=0
    for indices in partitions:
        selected=set(indices)
        a=[row for index,row in enumerate(pooled) if index in selected]
        b=[row for index,row in enumerate(pooled) if index not in selected]
        difference=abs(window_metric(b,metric)-window_metric(a,metric))
        extreme+=difference>=observed-1e-12; total+=1
    probability=extreme/total if exact else (extreme+1)/(total+1)
    return {'p_value':round(probability,6),'method':'exact_permutation' if exact else 'seeded_permutation_2000','permutations':total}


def compare_windows(rows,metric,window):
    if len(rows)<2*window: return {'data_status':'insufficient_sample','required_appearances':2*window,'signal':None}
    historical,recent=rows[-2*window:-window],rows[-window:]
    previous,current=window_metric(historical,metric),window_metric(recent,metric)
    if previous is None or current is None: return {'data_status':'missing_metrics','signal':None}
    delta=round(current-previous,2)
    result={'historical':previous,'recent':current,'absolute_change':delta,
        'relative_change_pct':None if previous==0 else round(delta/abs(previous)*100,2),
        'appearances_per_window':window,'signal':None,'data_status':'descriptive_only'}
    if window>=5 and all(window_metric([row],metric) is not None for row in historical+recent):
        test=permutation_comparison(historical,recent,metric)
        threshold=5 if metric.endswith('_pct') or metric=='passes_completed_per_90' else 0.1
        result.update(test,data_status='exploratory_comparison')
        if test['p_value']<=0.05 and abs(delta)>=threshold:
            result['signal']='increase' if delta>0 else 'decrease'
    return result


def season_summaries(db,player_id,source,metric):
    expressions=[Season.id,Season.name,func.count(PlayerMatchStats.id)]
    for name in METRICS:
        column=getattr(PlayerMatchStats,name); expressions.extend((func.sum(column),func.count(column)))
    query=db.query(*expressions).select_from(PlayerMatchStats).join(Match,Match.id==PlayerMatchStats.match_id).join(Season,Season.id==Match.season_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id)
    query=query.filter(PlayerMatchStats.player_id==player_id,PlayerMatchStats.minutes_played>0,Match.status=='finished',func.lower(func.coalesce(ImportBatch.source,'manual'))==source)
    results=[]; previous=None
    for row in query.group_by(Season.id,Season.name,Season.starts_on).order_by(Season.starts_on,Season.id).all():
        totals={name:(row[3+index*2] if row[4+index*2]==row[2] else None) for index,name in enumerate(METRICS)}
        value=metrics_from_totals(totals)[metric]
        results.append({'season_id':row[0],'season':row[1],'appearances':row[2],'value':value,
            'change_from_previous':None if previous is None or value is None else round(value-previous,2)})
        previous=value
    return results


def performance_trends(db,player_id,metric='goals_per_90',season_id=None,window=5,min_samples=None,data_source=None):
    required(db,Player,player_id)
    if metric not in METRIC_DEFINITIONS: raise HTTPException(status_code=422,detail='Unsupported trend metric')
    min_samples=min(3,window) if min_samples is None else min_samples
    if min_samples>window: raise HTTPException(status_code=422,detail='Minimum samples cannot exceed the rolling window')
    season_id=resolve_season(db,season_id,player_id)
    source=func.lower(func.coalesce(ImportBatch.source,'manual'))
    query=db.query(PlayerMatchStats,Match.kickoff_at,Match.id,source).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id)
    query=query.filter(PlayerMatchStats.player_id==player_id,PlayerMatchStats.minutes_played>0,Match.status=='finished',Match.season_id==season_id)
    providers=sorted(row[0] for row in db.query(source).select_from(PlayerMatchStats).join(Match,Match.id==PlayerMatchStats.match_id).outerjoin(ImportBatch,ImportBatch.id==PlayerMatchStats.import_batch_id).filter(PlayerMatchStats.player_id==player_id,Match.status=='finished',Match.season_id==season_id).distinct())
    selected=data_source.strip().lower() if data_source is not None else (providers[0] if len(providers)==1 else None)
    result={'player_id':player_id,'season_id':season_id,'metric':metric,'window':window,'min_samples':min_samples,
        'data_source':selected,'available_sources':providers,'observations':[],'season_comparisons':[],
        'methodology':'Observed positive-minute appearances in chronological order. Rolling rates use summed numerators/denominators, preserving missing data. Up to 1000 latest appearances are shown.',
        'limitations':'Exploratory permutation signals require at least five appearances per window and exchangeable observations. They do not adjust for opposition, roles, dependence between matches or multiple testing.'}
    if selected is None: return {**result,'data_status':'source_selection_required' if providers else 'no_data'}
    raw=query.filter(source==selected).order_by(Match.kickoff_at.desc(),Match.id.desc()).limit(1001).all()
    truncated=len(raw)>1000; raw=list(reversed(raw[:1000]))
    values=[{name:getattr(row[0],name) for name in METRICS} for row in raw]
    rolling=rolling_values(values,metric,window,min_samples)
    result['observations']=[{'match_id':row[2],'kickoff_at':row[1],'minutes_played':row[0].minutes_played,
        'value':window_metric([values[index]],metric),'rolling_average':rolling[index],
        'rolling_appearances':min(index+1,window)} for index,row in enumerate(raw)]
    result['comparison']=compare_windows(values,metric,window)
    result['season_comparisons']=season_summaries(db,player_id,selected,metric)
    return {**result,'truncated':truncated,'data_status':'available' if raw else 'no_data'}
