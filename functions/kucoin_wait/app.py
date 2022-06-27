import logging
import os
from kucoin.client import Client
from utilities import load_json
logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    # Set up KuCoin client
    kucoin_secrets = load_json(os.environ['SECRET_BUCKET'], os.environ['KUCOIN_SECRET_KEY'])
    client = Client(kucoin_secrets['key'], kucoin_secrets['secret'], kucoin_secrets['passphrase'])
        
    # Check LTC balance is not zero and is all available to use in the trade account
    LTC_acc = client.get_accounts('LTC', 'trade')[0]
    
    if (float(LTC_acc['balance']) > 0) and (LTC_acc['balance'] == LTC_acc['available']):
        return 1
        
    elif (float(LTC_acc['balance']) >= 0) and (LTC_acc['balance'] != LTC_acc['available']):
        return 0
        
    else:
        return -1