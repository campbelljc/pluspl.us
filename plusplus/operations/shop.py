from .. import config

shop_options = [
    (1, 0, 'Hint for Assignment 1 private test')
]

def get_shop_option(option_num):
    assert shop_options[option_num-1][0] == option_num
    return shop_options[option_num-1]

def shop_text(team):
    option_texts = []
    for option in shop_options:
        option_texts.append(f'** [{option[0]}] ** (** {option[1]} coins) ** {option[2]}')
    
    option_texts += ['*Other options will be available as the term continues.*']
    
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
                "text": "\n".join(option_texts)
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
