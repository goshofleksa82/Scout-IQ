from test_matches import match_data


def test_profile_provenance_and_source_filter_do_not_invent_updates(admin_client,match_data):
    player=match_data['players'][0]
    empty=admin_client.get(f'/analytics/players/{player}/provenance').json()
    assert empty['player_record']['imported_at'] is None
    assert empty['player_record']['rights_basis'] is None
    assert empty['match_statistics']==[]
    assert admin_client.post(f'/matches/{match_data["match"]}/player-stats',json={'player_id':player,'minutes_played':90,'goals':1,'assists':0}).status_code==201
    query=f'/analytics/players/{player}/metrics?season_id={match_data["season"]}'
    known=admin_client.get(query+'&data_source=manual').json()
    assert known['metrics']['goals_per_90']==1 and known['updated_at']
    other=admin_client.get(query+'&data_source=other-provider').json()
    assert other['matches_recorded']==0 and other['updated_at'] is None
    assert all(value is None for value in other['metrics'].values())
    provenance=admin_client.get(f'/analytics/players/{player}/provenance?season_id={match_data["season"]}').json()
    assert provenance['match_statistics'][0]['source']=='manual'
    assert provenance['match_statistics'][0]['last_updated_at']==known['updated_at']
    assert 'user_id' not in str(provenance)
