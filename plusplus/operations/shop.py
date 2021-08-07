from .. import config


def shop_text(team):
    options = [
        '** [1] ** (** X coins) ** Hint for Assignment 1 private test',
        '*Other options will be available as the term continues.*'
    ]
    
    shop_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! Here's what you can exchange for your coins. "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(options)
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Type **<@{team.bot_user_id}> exchange *[option_number]* ** to initiate an exchange."
            }
        }
    ]
    return shop_block
