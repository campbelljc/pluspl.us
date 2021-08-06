from plusplus.operations.points import update_points
from plusplus.operations.leaderboard import generate_leaderboard
from plusplus.operations.help import help_text
from plusplus.operations.reset import generate_reset_block
from plusplus.models import db, SlackTeam, Thing
from flask import request
import re

user_exp = re.compile(r"<@([A-Za-z0-9]+)> *(\+\+|\-\-|==)")
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
    # ignore retries
    if request.headers.get('X-Slack-Retry-Reason'):
        return "Status: OK"

    event = event_data['event']
    subtype = event.get('subtype', '')

    # is the message from a thread
    # hacky workaround to determine the event subtype due to a bug
    # with Slack as of 6/1/2020 where subtypes are not sent over the events API
    # https://api.slack.com/events/message/message_replied
    if 'thread_ts' in event and event['ts'] != event['thread_ts']:
        # has to be a top-level message if thread_ts is provided
        thread_ts = event['thread_ts']
    else:
        thread_ts = None

    # ignore bot messages
    if subtype == 'bot_message':
        return "Status: OK"

    # ignore edited messages
    if subtype == 'message_changed':
        return "Status: OK"

    message = event.get('text').lower()
    user = event.get('user').lower()
    channel = event.get('channel')
    channel_type = event.get('channel_type')

    # load/update team
    team = SlackTeam.query.filter_by(id=event_data['team_id']).first()
    team.update_last_access()
    db.session.add(team)
    db.session.commit()

    user_match = user_exp.match(message)
    thing_match = thing_exp.match(message)
    # Hacky way right now to determine what the reason is
    # going to assume all reasons start with the word 'for'
    # TODO can probably also start with 'because'
    if ' for ' in message:
        reason = message.split('for')[-1]
    elif ' because ' in message:
        reason = 'because ' + message.split('because')[-1]
    else:
        reason = "[no reason provided]"
    
    if (user_match or thing_match) and user != ADMIN_USER:
        post_message('Sorry, only the server admin can add points!', team, channel, thread_ts=thread_ts)
        return "OK", 200

    if user_match:
        # handle user point operations
        found_user = user_match.groups()[0].strip()
        operation = user_match.groups()[1].strip()
        thing = Thing.query.filter_by(item=found_user.lower(), team=team).first()
        if not thing:
            thing = Thing(item=found_user.lower(), points=[], user=True, team_id=team.id)
            db.session.add(thing)
            db.session.commit()
            
        message_to_admin, message_to_user = update_points(thing, operation, user, reason=reason, is_self=(user == found_user))
        post_message(message_to_admin, team, channel, thread_ts=thread_ts)
        post_message(message_to_user, team, found_user.upper())
        
        print("Processed " + thing.item)
    #elif thing_match:
    #    # handle thing point operations
    #    found_thing = thing_match.groups()[0].strip()
    #    operation = thing_match.groups()[1].strip()
    #    thing = Thing.query.filter_by(item=found_thing.lower(), team=team).first()
    #    if not thing:
    #        thing = Thing(item=found_thing.lower(), points=[], user=False, team_id=team.id)
    #        db.session.add(thing)
    #        db.session.commit()
    #        
    #    message = update_points(thing, operation, user, reason=reason)
    #    post_message(message, team, channel, thread_ts)
    #    print("Processed " + thing.item)
    elif "leaderboard" in message and team.bot_user_id.lower() in message:
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=generate_leaderboard(team=team)
        )
        print("Processed leaderboard for team " + team.id)
    #elif "loserboard" in message and team.bot_user_id.lower() in message:
    #    team.slack_client.chat_postMessage(
    #        channel=channel,
    #        blocks=generate_leaderboard(team=team, losers=True)
    #    )
    #    print("Processed loserboard for team " + team.id)
    elif "help" in message and (team.bot_user_id.lower() in message or channel_type == "im"):
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=help_text(team)
        )
        print("Processed help for team " + team.id)
    #elif "reset" in message and team.bot_user_id.lower() in message:
    #    team.slack_client.chat_postMessage(
    #        channel=channel,
    #        blocks=generate_reset_block()
    #    )
    return "OK", 200
