from .. import config

shop_options = [
    # opt. number, num. coins, description
    
    #(1,    100, 'number of passing vs. failing private tests on your Assignment 1 submission'),
    #(2,   1000, 'information on the first failing private test for your Assignment 1 submission'),
    
    #(3,   '10% of your coin balance', 'contribute to final hint pool')
    #(3, 100000, 'sticker (see discussion board for types) (first come first serve)')
]

def get_shop_option(option_num):
    assert shop_options[option_num-1][0] == option_num
    return shop_options[option_num-1]

def shop_text(team, coins):
    option_texts = []
    for option in shop_options:
        option_texts.append(f'*[{option[0]}]* (*{option[1]} coins*) {option[2]}')
    
    option_texts += ['No options are currently available.\nOther options will be available as the term continues.', f'You currently have {coins} coins.']
    
    shop_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! Here's what you can redeem for your coins. (More details can be found on the discussion board.)"
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
                "text": f"Type *<@{team.bot_user_id}> redeem [option_number]* to redeem. E.g., *<@{team.bot_user_id}> redeem 1*"
            }
        }
    ]
    return shop_block
