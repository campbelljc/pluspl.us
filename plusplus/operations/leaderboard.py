from ..models import Thing, db
import json


def generate_leaderboard(team=None):
    ordering = Thing.total_points.desc()
    user_args = {"user": True, "team": team}
    
    all_users = Thing.query.filter_by(**user_args).order_by(ordering)
    total_coins = 0
    for user in all_users:
        total_coins += user.total_points
    
    top_ten = all_users.limit(10)
    
    # get all time top 10
    all_time_pts = []
    for user in all_users:
        user_pts = 0
        for point in user.points:
            if point.value > 0:
                user_pts += point.value
        all_time_pts.append((user_pts, user))
    all_time_pts.sort(reverse=True, key=lambda tup: tup[0])
    
    top_all_time = all_time_pts[1:11] # hack: remove me
    total_coins -= all_time_pts[0][0] # ^
    
    #ordering_all_time = Thing.total_all_time_points.desc()
    #all_time_top_ten = Thing.query.filter_by(**user_args).order_by(ordering_all_time)
    
    formatted_users = [f"<@{user.item.upper()}> ({user.total_points})" for user in top_ten]
    numbered_users = generate_numbered_list(formatted_users)

    formatted_all_time_users = [f"<@{user.item.upper()}> ({pts})" for pts, user in top_all_time]
    numbered_all_time_users = generate_numbered_list(formatted_all_time_users)

    header = f"Here's the current leaderboard.\nTotal coins in circulation: {total_coins}.\nTotal number of students with points:{all_users.count()-1}"
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
