from .. import config

shop_options = [
    # opt. number, num. coins, description
    (1,    100, 'number of passing vs. failing private tests on your submission for Assignment 1'),
    (2,   1000, 'information (test title, expected output, submission output) on first failing private test on your submission for Assignment 1'),
    (3, 100000, 'sticker (see discussion board for types) (first come first serve)')
]

def get_shop_option(option_num):
    assert shop_options[option_num-1][0] == option_num
    return shop_options[option_num-1]

def shop_text(team):
    option_texts = []
    for option in shop_options:
        option_texts.append(f'*[{option[0]}]* (*{option[1]} coins*) {option[2]}')
    
    option_texts += ['*Other options will be available as the term continues.*']
    
    shop_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! Here's what you can redeem for your coins. "
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
                "text": f"Type *<@{team.bot_user_id}> redeem [option_number]* to redeem."
            }
        }
    ]
    return shop_block
