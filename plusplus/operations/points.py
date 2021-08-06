from plusplus.models import db
import json
import random


def update_points(thing, end, user, reason, is_self=False):
    #if is_self and end != '==':  # don't allow someone to plus themself
    #    operation = "self"
    if end == "++":
        operation = "plus"
        point = thing.increment(reason)
    elif end == "--":
        operation = "minus"
        point = thing.decrement(reason)
    else:
        operation = "equals"
        
    if operation in ["plus", "minus"]:
        db.session.add(thing)
        db.session.add(point)
        db.session.commit()
    
    return generate_string(thing, operation, reason, 1)


def generate_string(thing, operation, reason, pt_increase):    
    if thing.user:
        formatted_thing = f"<@{thing.item.upper()}>"
    else:
        formatted_thing = thing.item

    msg_to_admin = ''

    points = thing.total_points
    points_word = "points" if points > 1 else "point"
    points_string = f"{points} {points_word}"
    with open("plusplus/strings.json", "r") as strings:
        parsed = json.load(strings)
        if operation in ["plus", "minus"]:
            exclamation = random.choice(parsed[operation])
            random_msg = random.choice(parsed[operation + "_points"])
            points = random_msg.format(thing=formatted_thing, points_string=points_string)
            msg_to_admin = f"{exclamation} {points}"
        elif operation == "self":
            msg_to_admin = random.choice(parsed[operation]).format(thing=formatted_thing)
        elif operation == "equals":
            msg_to_admin = random.choice(parsed[operation]).format(thing=formatted_thing, points_string=points_string)
    
    msg_to_user = f'Congrats! You have been awarded {pt_increase} points for {reason}. You now have a total of {points} points.'
    
    return msg_to_admin, msg_to_user