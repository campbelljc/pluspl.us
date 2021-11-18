from plusplus.operations.points import update_points
from plusplus.operations.leaderboard import generate_leaderboard
from plusplus.operations.help import help_text
from plusplus.operations.shop import *
from plusplus.operations.reset import generate_reset_block
from plusplus.models import db, SlackTeam, Thing
from plusplus import config
from flask import request
import re
import random
import codepost

user_exp = re.compile(r"<@([A-Za-z0-9]+)> *(\+\+|\-\-|==|\+\=|\-\=) ([0-9]+)")
thing_exp = re.compile(r"#([A-Za-z0-9\.\-_@$!\*\(\)\,\?\/%\\\^&\[\]\{\"':; ]+)(\+\+|\-\-|==)")              

GENERAL_CHANNEL = 'C02DZ5ACZ1U'

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

    orig_message = event.get('text')
    message = orig_message.lower()
    user = event.get('user').lower()
    channel = event.get('channel')
    channel_type = event.get('channel_type')
    
    if user.lower() == config.SLACK_USER_ID.lower():
        return "Status: OK" # ignore messages sent by bot

    # load/update team
    team = SlackTeam.query.filter_by(id=event_data['team_id']).first()
    team.update_last_access()
    db.session.add(team)
    db.session.commit()
    
    if "leaderboard" in message and team.bot_user_id.lower() in message:
        user = Thing.query.filter_by(item=user.lower(), team=team).first()
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=generate_leaderboard(user, team=team)
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
        user = Thing.query.filter_by(item=user.lower(), team=team).first()
        team.slack_client.chat_postMessage(
            channel=channel,
            blocks=shop_text(team, user.total_points if user is not None else 0)
        )
        print("Processed shop for team " + team.id)
        return "OK", 200
    elif "redeem" in message and (team.bot_user_id.lower() in message or channel_type == "im"):
        option = message.split("redeem")[-1].strip().replace("*", "")
        if channel.lower() == GENERAL_CHANNEL.lower():
            post_message(f'To redeem something, please open a DM with CoinsBot and enter your commands there. Thanks!', team, channel, thread_ts=thread_ts)
            return "OK", 200
        print("redeem", message, user, channel)
        unrecognized = ''
        for c in option:
            if not c.isdigit():
                unrecognized += c
        if len(unrecognized) > 0:
            post_message(f'You entered "{option}", but I did not recognize "{unrecognized}".', team, channel, thread_ts=thread_ts)
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
                    post_message(f'This option costs {pts} coins, but you have {user.total_points}.', team, channel, thread_ts=thread_ts)
                else:
                    # send message back & send message to TA
                    assert user.ta_id is not None
                    status, message = process_redeem(user, team, channel, thread_ts, option_num)
                    if not status:
                        message += '\nCould not redeem (points balance unchanged).'
                        post_message(message, team, channel, thread_ts=thread_ts)
                    else:
                        update_points(user, '-=', pts, reason=f'Redeemed {pts} points for {desc}') # discard generated msgs
                        message += f'\n\nYour point balance is now {user.total_points}.'
                        post_message(message, team, channel, thread_ts=thread_ts)
                        #post_message(f'Student <@{user.item.upper()}> spent {pts} points to redeem "{desc}".', team, user.ta_id.upper())
                        post_message(f'Student <@{user.item.upper()}> spent {pts} points to redeem "{desc}". They received the following message:\n{message}', team, config.SLACK_ADMIN_USER_ID.upper())
        
        print("Processed redeem for team " + team.id)
        return "OK", 200
    elif "msg" in message and (team.bot_user_id.lower() in message or channel_type == "im") and user == config.SLACK_ADMIN_USER_ID:
        msg = orig_message.split("msg")[-1].strip().replace("*", "")
        post_message(msg, team, GENERAL_CHANNEL)

    # handle user point operations

    user_match = user_exp.match(message)
    if not user_match or user != config.SLACK_ADMIN_USER_ID:
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

    this_assignment = this_course.assignments.by_name(name="Assignment 3")
    if this_assignment is None:
        raise Exception("ERROR: couldn't find assignment with name %s in specified course" % ("Assignment 3"))

    # retrieve list of assignment's submissions
    submissions = this_assignment.list_submissions(student=email)
    return submissions

def process_redeem(user, team, channel, thread_ts, option_num):
    #if str(option_num) == "1" or str(option_num) == "2":
    #    return False, "It is not yet possible to redeem coins for Assignment 3. Please watch the discussion board as we will post there when the option will be available."
    
    #return False, "This option is not available at this time."
    
    if str(option_num) == "1": # number of passing vs. failing private tests on your submission for Assignment 3
        submissions = get_assignment_submission(team, user)
        if len(submissions) == 0:
            message = f"Could not find a submission for Assignment 3 with email {email}. Are you sure you have made a submission? If so, please check that your Slack and codePost emails are identical and let your TA know if not."
            return False, message
    
        submission = submissions[0]
        
        timeout = False
        
        test_cases = {}
        test_cats = {}
        num_tests, passed_tests = 0, 0
        for test in submission.tests:
            if test.testCase not in test_cases:
                test_cases[test.testCase] = codepost.test_case.retrieve(id=test.testCase)
                test_cat = test_cases[test.testCase].testCategory
                if test_cat not in test_cats:
                    test_cats[test_cat] = codepost.test_category.retrieve(id=test_cat)
        
            test_case = test_cases[test.testCase]
            test_cat = test_cats[test_case.testCategory]
        
            if '(private)' not in test_cat.name:
                continue
        
            num_tests += 1
            if test.passed:
                passed_tests += 1
            
            if 'Operation Timed Out' in test.logs:
                timeout = True
        
        message = f"The results of the private tests on your latest Assignment 3 submission to codePost are as follows:\nPassed: {passed_tests}\nFailed: {num_tests-passed_tests}\nTotal tests: {num_tests}\n\nNote that the grade for an assignment is not fully decided by the private tests. Our TAs will also check that your submission complies with the assignment's instructions regarding style and other issues as listed on the first page of the PDF.\n\nAlso, note that the number of private tests are subject to change, so these totals may not entirely reflect the final grade on the assignment.\n\nFurther, certain public tests (e.g., invalid function test, amongst others) also have point values, so make sure to check those as well as they are not included here."
        
        if timeout:
            message += "\n\n*Note: A timeout error was detected in your submission. When a test times out, all subsequent tests also time out, which can cause a large number of tests to appear as failed when they would pass if the bug affecting the timed out test was fixed.*"
        
        return True, message
        
    elif str(option_num) == "2":
        submissions = get_assignment_submission(team, user)
        if len(submissions) == 0:
            message = f"Error: Could not find a submission for Assignment 3 with email {email}. Are you sure you have made a submission? If so, please check that your Slack and codePost emails are identical and let your TA know if not."
            return False, message
        submission = submissions[0]
        
        test_cases = {}
        test_cats = {}

        failed_test = None
        
        student_tests = submission.tests[:]
        student_tests.sort(key=lambda test: test.testCase)
        for test in student_tests:
            if test.testCase not in test_cases:
                test_cases[test.testCase] = codepost.test_case.retrieve(id=test.testCase)
                test_cat = test_cases[test.testCase].testCategory
                if test_cat not in test_cats:
                    test_cats[test_cat] = codepost.test_category.retrieve(id=test_cat)
        
            test_case = test_cases[test.testCase]
            test_cat = test_cats[test_case.testCategory]
        
            if '(private)' not in test_cat.name:
                continue
        
            if not test.passed:
                failed_test = test
                break

        if failed_test is None:
            message = f"Error: Your submission for Assignment 3 is not failing any tests at the moment."
            return False, message
        
        test_logs = failed_test.logs + "\n" + test_case.explanation
        test_desc = test_case.description
        test_cat_id = test_case.testCategory
        test_expl = test_case.explanation
        if len(test_expl) > 0:
            test_expl = f"({text_expl})"
        test_cat = codepost.test_category.retrieve(id=test_cat_id)
        test_cat_name = test_cat.name
        
        message = f"The first failing private test for your Assignment 3 submission is as follows:\nTest category: {test_cat_name}\nTest name: {test_desc} {test_expl}\nLogs: {test_logs}\n\nNote: Please do not discuss this private test with other students nor post on the discussion board about it."        
        return True, message
    else:
        message = "Sorry, that is not a valid option number to redeem. You can only choose an option from 1 to 3."
        return False, message
    
    '''   
    elif str(option_num) == "3":
        team.add_to_midterm_pool(1000)
        message = f"You have added 1000 points to the midterm hint pool. The pool is now at {team.midterm_pool_points}."
        if team.midterm_pool_points % 5000 == 0:
            post_message(f"The midterm points pool is now at {team.midterm_pool_points}. Further message will be posted after an additional 5000 is contributed.", team, GENERAL_CHANNEL)
        if team.midterm_pool_points % 30000 == 0:
            post_message(f"A midterm hint has been unlocked! Please check the discussion board later in the day.", team, GENERAL_CHANNEL)
            post_message(f"Let's flip a coin to see if one hint or two will be provided!", team, GENERAL_CHANNEL)
            post_message(f">>> random.randint(1, 2)", team, GENERAL_CHANNEL)
            post_message(f"{random.randint(1, 2)}", team, GENERAL_CHANNEL)
        return True, message
        #message = f"Please allow 1-3 days response time. Your TA will be in contact with you regarding sticker choice. Sticker choice is first come first serve, based on date of redemption."
        #return True, message
    '''
    