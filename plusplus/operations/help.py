from .. import config


def help_text(team):
    commands = ["• *{ping} leaderboard*: show the current high scores",
                "• *{ping} shop*: show the list of things available to redeem for coins",
                "• *{ping} help*: show this list of commands",
                "• *{ping} log*: show a list of your coin deposits and withdrawals",
                "• *{ping} redeem [x]*: redeem your coins for option [x] from the shop listing"]
    formatted_commands = list()
    for command in commands:
        formatted_commands.append(command.format(ping=f"<@{team.bot_user_id}>"))

    help_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! Here's a quick rundown on how to use <@{team.bot_user_id}>"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(formatted_commands)
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Still need help? Please get in touch with your TA!"
            }
        }
    ]
    return help_block
