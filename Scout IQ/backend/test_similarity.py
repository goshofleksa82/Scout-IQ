from copy import deepcopy
from app.services.similarity import normalized_similarity
from test_matches import match_data


def test_similarity_identical_profiles_normalization_and_stable_ties():
    rows=[{'player_id':1,'metrics':{'a':1,'b':100}},
          {'player_id':2,'metrics':{'a':1,'b':100}},
          {'player_id':3,'metrics':{'a':2,'b':200}}]
    first=normalized_similarity(rows,1,['a','b'])
    assert first['similar'][0]['player_id']==2 and first['similar'][0]['similarity']==100
    scaled=deepcopy(rows)
    for row in scaled: row['metrics']['b']*=1000
    second=normalized_similarity(scaled,1,['a','b'])
    assert [row['similarity'] for row in first['similar']]==[row['similarity'] for row in second['similar']]
    assert first==normalized_similarity(rows,1,['a','b'])


def test_constant_dimensions_do_not_divide_by_zero():
    rows=[{'player_id':1,'metrics':{'a':0,'b':1}},{'player_id':2,'metrics':{'a':0,'b':1}}]
    result=normalized_similarity(rows,1,['a','b'])
    assert result['similar'][0]['similarity']==100 and result['constant_features']==['a','b']


def test_similarity_api_missing_metrics_and_sample_compatibility(admin_client,match_data):
    match=match_data['match']; first,second,third=match_data['players']
    for player in (first,second):
        assert admin_client.post(f'/matches/{match}/player-stats',json={'player_id':player,'minutes_played':90,'goals':0,'assists':1,'tackles':2,'passes_attempted':50,'passes_completed':40}).status_code==201
    result=admin_client.get(f'/analytics/players/{first}/similar?min_minutes=0').json()
    assert result['data_status']=='available' and result['similar'][0]['player_id']==second
    assert result['similar'][0]['similarity']==100
    assert admin_client.get(f'/analytics/players/{first}/similar').json()['data_status']=='insufficient_minutes'
    assert admin_client.get(f'/analytics/players/{third}/similar?min_minutes=0').json()['data_status']=='no_match_data'
    assert admin_client.get(f'/analytics/players/{first}/similar?features=goals_per_90,assists_per_90').status_code==422
