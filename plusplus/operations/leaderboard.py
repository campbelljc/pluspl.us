from ..models import Thing
import json


def generate_leaderboard(team=None):
    header = "Here's the current leaderboard:"
    ordering = Thing.total_points.desc()
    user_args = {"user": True, "team": team}
    
    all_users = Thing.query.filter_by(**user_args).order_by(ordering)
    total_coins = 0
    for user in users:
        total_coins += user.total_points
    
    top_ten = all_users.limit(10)
    all_time_top_ten = Thing.query.filter_by(**user_args).order_by(Thing.total_all_time_points.desc())
    
    formatted_users = [f"<@{user.item.upper()}> ({user.total_points})" for user in top_ten]
    numbered_users = generate_numbered_list(formatted_users)

    formatted_all_time_users = [f"<@{user.item.upper()}> ({user.total_points})" for user in all_time_top_ten]
    numbered_all_time_users = generate_numbered_list(formatted_all_time_users)

    leaderboard_header = {"type": "section",
                          "text":
                              {
                                  "type": "mrkdwn",
                                  "text": header
                              }
                          }
    body = {
        "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total number of coins in circulation*: {total_coins}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Coin holders*:\n" + numbered_users
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*All-time coin earners (including coins already redeemed)*:\n" + numbered_all_time_users
                    }
                ]
    }

    leaderboard = [leaderboard_header, body]
    return json.dumps(leaderboard)


def generate_numbered_list(items):
    out = ""
    for i, item in enumerate(items, 1):
        out += f"{i}. {item}\n"
    if len(out) == 0:
        out = "Welp, nothing's here yet."
    return out
