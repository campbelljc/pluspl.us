from ..models import Thing, db
import json


def generate_leaderboard(asker, team=None):
    ordering = Thing.total_points.desc()
    user_args = {"user": True, "team": team}
    
    all_users = Thing.query.filter_by(**user_args).order_by(ordering)
    total_coins = 0
    start_number = -1
    current_and_adjacent = {}
    for i, user in enumerate(all_users):
        total_coins += user.total_points
        if i > 10 and user is not None and user.id == asker.id:
            start_number = i-1
            current_and_adjacent = {
                all_users[k].item.upper(): all_users[k].total_points for k in range(i-1, i+2)
            }
    
    top_ten = all_users.limit(10)
    
    # get all time top 10
    
    mods = {}
    
    all_time_pts = []
    for user in all_users:
        user_pts = 0
        for point in user.points:
            if point.value > 0:
                user_pts += point.value
        if user.item.upper() in mods:
            user_pts += mods[user.item.upper()]
        all_time_pts.append((user_pts, user))
    all_time_pts.sort(reverse=True, key=lambda tup: tup[0])
    
    start_number_all_time = -1
    current_and_adjacent_all_time = {}
    for i, (user_pts, user) in enumerate(all_time_pts):
        if i > 10 and user is not None and user.id == asker.id:
            start_number_all_time = i-1
            current_and_adjacent_all_time = {
                user.item.upper(): user_pts for k in range(i-1, i+2)
            }
    
    top_all_time = all_time_pts[1:11] # hack: remove me
    if len(all_time_pts) > 0:
        total_coins -= all_time_pts[0][0] # ^
    
    #ordering_all_time = Thing.total_all_time_points.desc()
    #all_time_top_ten = Thing.query.filter_by(**user_args).order_by(ordering_all_time)
    
    # ***
    # make list of current top ten point holders
    # ***
    
    asker_in_top_ten = False
    formatted_users = []
    for i, user in enumerate(top_ten):
        formatted_users.append(f"<@{user.item.upper()}> ({user.total_points})")
        if user.id == asker.id:
            asker_in_top_ten = True
            formatted_users[-1] = "*" + formatted_users[-1] + "*"
    
    numbered_users = generate_numbered_list(formatted_users)
    
    current_user_info = ""
    if not asker_in_top_ten:
        if len(current_and_adjacent) == 0:
            current_user_info = 'You currently have 0 coins.'
        else:
            # print current placement and person directly above and below.
            adj = [f"<@{x}> ({y})" for x, y in current_and_adjacent.items()]
            current_user_info = generate_numbered_list(adj, start_number)
    
    # ***
    # make list of all time top ten point holders
    # ***
    
    asker_in_all_time_top_ten = False
    formatted_all_time_users = []
    for pts, user in top_all_time:
        formatted_all_time_users.append(f"<@{user.item.upper()}> ({pts})")
        if user.id == asker.id:
            asker_in_all_time_top_ten = True
            formatted_all_time_users[-1] = "*" + formatted_all_time_users[-1] + "*"
    
    numbered_all_time_users = generate_numbered_list(formatted_all_time_users)
    
    current_user_all_time_info = ""
    if not asker_in_all_time_top_ten:
        if len(current_and_adjacent) == 0:
            current_user_all_time_info = 'You currently have 0 coins.'
        else:
            # print current placement and person directly above and below.
            adj = [f"<@{x}> ({y})" for x, y in current_and_adjacent_all_time.items()]
            current_user_all_time_info = generate_numbered_list(adj, start_number_all_time)
    
    header = f"Here's the current leaderboard.\nTotal coins in circulation: {total_coins}.\nTotal number of students with coins: {all_users.count()-1}"
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
                        "text": f"*Coin holders*:\n" + numbered_users + "\n\n" + current_user_info
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*All-time coin earners (including coins already redeemed)*:\n" + numbered_all_time_users + "\n\n" + current_user_all_time_info
                    }
                ]
    }

    leaderboard = [leaderboard_header, body]
    return json.dumps(leaderboard)


def generate_numbered_list(items, start=1):
    out = ""
    for i, item in enumerate(items, start):
        out += f"{i}. {item}\n"
    if len(out) == 0:
        out = "Welp, nothing's here yet."
    return out
