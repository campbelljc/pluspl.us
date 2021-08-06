from .. import config


def help_text(team):
    commands = ["• *{ping} leaderboard*: get the current high scoring people and things",
                "• *{ping} shop*: show the list of things available to exchange for coins"]
    formatted_commands = list()
    for command in commands:
        formatted_commands.append(command.format(ping=f"<@{team.bot_user_id}>"))

    help_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey hey! Here's a quick rundown on how to use <@{team.bot_user_id}>"
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
                "text": f"Still need help? Send us an email at {config.SUPPORT_EMAIL}!"
            }
        }
    ]
    return help_block
