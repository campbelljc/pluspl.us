from ..models import Thing, db
from ..config import SLACK_ADMIN_USER_ID
import json


def generate_leaderboard(asker, team=None):
    ordering = Thing.total_points.desc()
    user_args = {"user": True, "team": team}
    
    all_users = Thing.query.filter_by(**user_args).order_by(ordering)
    total_coins = 0
    start_number = -1
    current_and_adjacent = {}
    for i, user in enumerate(all_users):
        if user.item.lower() == SLACK_ADMIN_USER_ID.lower():
            continue
        
        total_coins += user.total_points
        if i > 10 and user is not None and user.id == asker.id:
            start_number = i-1
            current_and_adjacent = {
                all_users[k].item.upper(): all_users[k].total_points for k in range(i-1, i+2)
            }
    
    top_ten = all_users.limit(11)
    
    # get all time top 10
    
    mods = {
        'U043XA6BVLN': -2500,
        'U042RBZ6C6A': -1500,
        'U042PCQJ4CW': -250,
        'U0448D6F61J': -1500,
        'U043RCXKY7R': -1500,
        'U0446C256MA': -1500,
        'U042V135WKX': -1500,
        'U043AKJCEKB': -250,
        'U044TKPR72L': -1000,
        'U042HDP422K': -1250,
        'U042FEAL4PR': -1250,
        
        'U042DDB3J9M': -550,
        'U042FEALL79': -500,
        'U042HDNF17H': -500,
        'U042HDZS2TH': -500,
        'U042RBY46LE': -500,
        'U042RBZ6C6A': -500,
        'U042RC2LYMU': -500,
        'U042RCDAVRC': -500,
        'U042T2EJTPX': -500,
        'U042T2FKE8M': -500,
        'U042V1ER7B7': -500,
        'U042V1T8F0V': -500,
        'U042W1FG6MQ': -500,
        'U0430DPHD5J': -500,
        'U0430DUTGSY': -500,
        'U0430E09468': -500,
        'U0438KVQ19P': -500,
        'U043AJK7UBB': -500,
        'U043AJVF2G1': -500,
        'U043AK2SR7B': -500,
        'U043AK41SAV': -500,
        'U043MMDGG8G': -500,
        'U0443U6T7L2': -1000,
        'U045XRFGMB8': -500,
        'U046NTT2X5M': -1000
    }
    
    all_time_pts = []
    for user in all_users:
        if user.item.lower() == SLACK_ADMIN_USER_ID.lower():
            continue
        
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
    
    top_all_time = all_time_pts[:10]
        
    # ***
    # make list of current top ten point holders
    # ***
    
    asker_in_top_ten = False
    formatted_users = []
    for i, user in enumerate(top_ten[1:]):
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
