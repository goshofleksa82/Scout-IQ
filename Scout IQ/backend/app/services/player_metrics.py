from app.models import Player

def per90(player: Player, metric: str) -> float:
    if metric == 'goals_per_90':
        count = player.goals
    elif metric == 'assists_per_90':
        count = player.assists
    else:
        count = player.goals + player.assists
    return round(count * 90 / player.minutes_played, 2)


def comparison_stats(player: Player) -> dict:
    data = {
        'name': player.name,
        'club': player.club,
        'position': player.position,
        'goals': player.goals,
        'assists': player.assists,
        'minutes_played': player.minutes_played,
        'goals_per_90': None,
        'assists_per_90': None,
        'goal_contributions_per_90': None,
    }
    if player.minutes_played > 0:
        for metric in ('goals_per_90', 'assists_per_90', 'goal_contributions_per_90'):
            data[metric] = per90(player, metric)
    return data

