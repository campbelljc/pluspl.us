from plusplus.operations.points import update_points
from plusplus.operations.leaderboard import generate_leaderboard
from plusplus.operations.help import help_text
from plusplus.operations.shop import *
from plusplus.operations.reset import generate_reset_block
from plusplus.models import db, SlackTeam, Thing
from plusplus import config
from flask import request
import re
import codepost

user_exp = re.compile(r"<@([A-Za-z0-9]+)> *(\+\+|\-\-|==|\+\=|\-\=) ([0-9]+)")
thing_exp = re.compile(r"#([A-Za-z0-9\.\-_@$!\*\(\)\,\?\/%\\\^&\[\]\{\"':; ]+)(\+\+|\-\-|==)")              


def get_id_for_name(team, name):
    response = team.slack_client.users_list()
    users = response["members"]

    for user in users:
        if user['name'] == name:
            return user['id']
    return None

def get_email_for_id(team, user_id):
    response = team.slack_client.users_list()
    users = response["members"]

    for user in users:
        if user['id'].lower() == user_id.lower():
            return user['profile']['email']
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
    elif "redeem" in message and (team.bot_user_id.lower() in message or channel_type == "im"):
        option = message.split("redeem")[-1].strip()
        if not all(c.isdigit() for c in option):
            post_message('Did not recognize that option. Did you enter a number?', team, channel, thread_ts=thread_ts)
        else:
            option = int(option)
            option_info = get_shop_option(option)
            option_num, pts, desc = option_info
            
            # check if user has enough points
            user = Thing.query.filter_by(item=user.lower(), team=team).first()
            if not user:
                post_message('Your user ID is not recognized (this can happen if you have no coins yet).', team, channel, thread_ts=thread_ts)
            else:
                if user.total_points < pts:
                    post_message(f'This option costs {pts}, but you only have {user.total_points}.', team, channel, thread_ts=thread_ts)
                else:
                    # send message back & send message to TA
                    assert user.ta_id is not None
                    if process_redeem(user, team, channel, thread_ts, option_num):
                        post_message(f'Your point balance is now {user.total_points}.', team, channel, thread_ts=thread_ts)
                        update_points(user, '-=', pts, reason=f'Redeemed {pts} points for {desc}') # discard generated msgs
                        post_message(f'Student <@{user.item.upper()}> spent {pts} points to redeem {desc}.', team, user.ta_id.upper())
                    else:
                        post_message(f'Error - could not redeem. Point balance unchanged.', team, channel, thread_ts=thread_ts)
        
        print("Processed redeem for team " + team.id)
        return "OK", 200
        

    # handle user point operations

    user_match = user_exp.match(message)
    if not user_match:
        return "OK", 200
    
    if user != config.SLACK_ADMIN_USER_ID:
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
    
    message_to_admin, message_to_user = update_points(user, operation, num_pts, reason=reason, is_self=(user == found_user))
    post_message(message_to_admin, team, channel, thread_ts=thread_ts)
    post_message(message_to_user, team, found_user.upper())
    
    print("Processed " + user.item)
    return "OK", 200

def get_assignment_submission(team, user):
    email = get_email_for_id(team, user.item)
    
    codepost.configure_api_key(api_key=config.CODEPOST_API_TOKEN)

    course_list = codepost.course.list_available(name=config.COURSE_CODE, period=config.COURSE_TERM)
    if len(course_list) == 0:
        raise Exception("Couldn't find course with name %s and period %s" % (config.COURSE_CODE, config.COURSE_TERM))
    this_course = course_list[0]

    this_assignment = this_course.assignments.by_name(name="Assignment 1")
    if this_assignment is None:
        raise Exception("ERROR: couldn't find assignment with name %s in specified course" % ("Assignment 1"))

    # retrieve list of assignment's submissions
    submissions = this_assignment.list_submissions(student=email)
    return submissionss

def process_redeem(user, team, channel, thread_ts, option_num):
    if str(option_num) == "1": # number of passing vs. failing private tests on your submission for Assignment 1
        submissions = get_assignment_submission(team, user)
        if len(submissions) == 0:
            post_message(f"Could not find a submission for Assignment 1 with email {email}. Are you sure you have made a submission? If so, please check that your Slack and codePost emails are identical and let your TA know if not.", team, channel, thread_ts=thread_ts)
            return False
    
        submission = submissions[0]
        
        num_tests, passed_tests = 0, 0
        for test in submission.tests:
            num_tests += 1
            if test.passed:
                passed_tests += 1
        
        post_message(f"The results of the private tests on your latest Assignment 1 submission to codePost are as follows:\nPassed:{passed_tests}\nFailed:{num_tests-passed_tests}\nTotal tests:{num_tests}\n\nNote that the grade for an assignment is not fully decided by the private tests. Our TAs will also check that your submission complies with the assignment's instructions regarding style and other issues as listed on the first page of the PDF.", team, channel, thread_ts=thread_ts)
        
        return True
    
    elif str(option_num) == "2":
        submissions = get_assignment_submission(team, user)
        if len(submissions) == 0:
            post_message(f"Error: Could not find a submission for Assignment 1 with email {email}. Are you sure you have made a submission? If so, please check that your Slack and codePost emails are identical and let your TA know if not.", team, channel, thread_ts=thread_ts)
            return False
    
        submission = submissions[0]
        failed_test = None
        for test in submission.tests:
            if not test.passed:
                failed_test = test
                break
        if failed_test is None:
            post_message(f"Error: Your submission for Assignment 1 is not failing any tests at the moment.", team, channel, thread_ts=thread_ts)
            return False
        
        test_logs = failed_test.logs
        test_id = failed_test.testCase
        test_case = codepost.test_case.retrieve(id=test_id)
        test_desc = test_case.description
        test_cat_id = test_case.testCategory
        test_cat = codepost.test_category.retrieve(id=test_cat_id)
        test_cat_name = test_cat.name
        
        post_message(f"The first failing private test for your Assignment 1 submission is as follows:\nTest category: {test_cat_name}\nTest name: {test_desc}\nLogs: {test_logs}", team, channel, thread_ts=thread_ts)
        
        return True
        
    elif str(option_num) == "3":
        post_message(f"Please allow 1-3 days response time. Your TA will be in contact with you regarding sticker choice. Sticker choice is first come first serve, based on date of redemption.", team, channel, thread_ts=thread_ts)