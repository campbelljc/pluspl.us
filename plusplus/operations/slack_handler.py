from plusplus.operations.points import update_points
from plusplus.operations.leaderboard import generate_leaderboard
from plusplus.operations.help import help_text
from plusplus.operations.shop import shop_text
from plusplus.operations.reset import generate_reset_block
from plusplus.models import db, SlackTeam, Thing
from flask import request
import re

user_exp = re.compile(r"<@([A-Za-z0-9]+)> *(\+\+|\-\-|==|\+\=) ([0-9]+)")
thing_exp = re.compile(r"#([A-Za-z0-9\.\-_@$!\*\(\)\,\?\/%\\\^&\[\]\{\"':; ]+)(\+\+|\-\-|==)")

ADMIN_USER = 'u029u80gjf9'


def get_id_for_name(team, name):
    response = team.slack_client.users_list()
    users = response["members"]

    for user in users:
        if user['name'] == name:
            return user['id']
    return None


def post_message(message, team, channel, thread_ts=None):
    if thread_ts:
        team.slack_client.chat_postMessage(
            channel=channel,
            text=message,
            thread_ts=thread_ts
        )
    else:
        team.slack_client.chat_postMessage(
            channel=channel,
            text=message
        )


def process_incoming_message(event_data):
    if request.headers.get('X-Slack-Retry-Reason'):
        return "Status: OK" # ignore retries

    event = event_data['event']
    subtype = event.get('subtype', '')

    if subtype in ['bot_message' or 'message_changed']:
        return "Status: OK" # ignore bot/edited messages
        
    if 'thread_ts' in event and event['ts'] != event['thread_ts']:
        # has to be a top-level message if thread_ts is provided
        thread_ts = event['thread_ts']
    else:
        thread_ts = None # message not from a thread

    message = event.get('text').lower()
    user = event.get('user').lower()
    channel = event.get('channel')
    channel_type = event.get('channel_type')

    # load/update team
    team = SlackTeam.query.filter_by(id=event_data['team_id']).first()
    team.update_last_access()
    db.session.add(team)
    db.session.commit()
    
    if "leaderboard" in message and team.bot_user_id.lower() in message:
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=generate_leaderboard(team=team)
        )
        print("Processed leaderboard for team " + team.id)
        return "OK", 200
    elif "help" in message and (team.bot_user_id.lower() in message or channel_type == "im"):
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=help_text(team)
        )
        print("Processed help for team " + team.id)
        return "OK", 200
    elif "shop" in message and (team.bot_user_id.lower() in message or channel_type == "im"):
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=shop_text(team)
        )
        print("Processed shop for team " + team.id)
        return "OK", 200

    # handle user point operations

    user_match = user_exp.match(message)
    if not user_match:
        return "OK", 200
    
    if user != ADMIN_USER:
        post_message('Sorry, only the server admin can add points!', team, channel, thread_ts=thread_ts)
        return "OK", 200

    if ';ta_id=' in message:
        ta_id = message.split(';ta_id=')[1]
        message = message.split(';ta_id=')[0]
    else:
        ta_id = None
    
    found_user = user_match.groups()[0].strip()
    operation = user_match.groups()[1].strip()
    num_pts = int(user_match.groups()[2].strip())
    reason = message.split('for')[-1] if ' for ' in message else "[no reason provided]"        
    
    user = Thing.query.filter_by(item=found_user.lower(), team=team).first()
    if not user:
        assert ta_id is not None
        user = Thing(item=found_user.lower(), ta_id=ta_id, points=[], user=True, team_id=team.id)
        db.session.add(user)
        db.session.commit()
    
    message_to_admin, message_to_user = update_points(user, operation, user, num_pts, reason=reason, is_self=(user == found_user))
    post_message(message_to_admin, team, channel, thread_ts=thread_ts)
    post_message(message_to_user, team, found_user.upper())
    
    print("Processed " + user.item)
    return "OK", 200
