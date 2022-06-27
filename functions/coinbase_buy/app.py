import cbpro
import os
import time
import logging
from utilities import load_json
logging.getLogger().setLevel(logging.INFO)

def get_accounts(auth_client):
    """Gets fiat and crypto accounts in Coinbase pro account.
    
    Args:
        auth_client: Authenticated Coinbase client
        
    Returns:
        dict
    """
    # Get Coinbase Pro accounts
    acc_list = auth_client.get_accounts()
    
    # Put accounts in a dictionary
    acc_dict = {}
    for acc in acc_list:
        acc_dict[acc['currency']] = acc
        
        # Convert values from str to float
        for key in ['balance', 'hold', 'available']:
            acc_dict[acc['currency']][key] = float(acc_dict[acc['currency']][key])

    return acc_dict


def lambda_handler(event, context):
    try:
        # Load in Coinbase pro secrets and create authenticated client
        cbpro_secrets = load_json(os.environ['SECRET_BUCKET'], os.environ['COINBASE_SECRET_KEY'])
        auth_client = cbpro.AuthenticatedClient(cbpro_secrets['key'], cbpro_secrets['secret'], cbpro_secrets['passphrase'])
        
        # Get Coinbase pro accounts
        acc_dict = get_accounts(auth_client)
        
        # Log environment variables
        logging.info(f"Total monthly buy funds: £{os.environ['MONTHLY_FUND']}")
        logging.info(f"Buy frequency per month: {os.environ['MONTHLY_FREQ']}")
        logging.info(f"Ratio of ETH to buy: {os.environ['RATIO_ETH']}")
        logging.info(f"Ratio of BTC to buy: {os.environ['RATIO_BTC']}")
        
        RATIO_LTC = 1 - (float(os.environ['RATIO_ETH']) + float(os.environ['RATIO_BTC']))
        logging.info(f"Ratio of LTC to buy: {RATIO_LTC}")
        
        # Calculate how much to use to buy ETH and LTC
        BUY_GBP = int(os.environ['MONTHLY_FUND']) / int(os.environ['MONTHLY_FREQ'])
        BUY_ETH_GBP = BUY_GBP * float(os.environ['RATIO_ETH'])
        BUY_BTC_GBP = BUY_GBP * float(os.environ['RATIO_BTC'])
        BUY_LTC_GBP = BUY_GBP - (BUY_ETH_GBP + BUY_BTC_GBP)
        logging.info(f"GBP funds to use for this run: £{BUY_GBP}")
        logging.info(f"Amount of ETH to buy in GBP: £{BUY_ETH_GBP}")
        logging.info(f"Amount of BTC to buy in GBP: £{BUY_BTC_GBP}")
        logging.info(f"Amount of LTC to buy in GBP: £{BUY_LTC_GBP}")
    
        # Check there's enough money GBP in account to buy
        assert(acc_dict["GBP"]["balance"] > BUY_GBP), "Not enough GBP to buy crypto!"
    
        # Buy ETH and LTC
        resp = auth_client.place_market_order(
            product_id="ETH-GBP", 
            side="buy",
            funds=BUY_ETH_GBP
        )
        assert("message" not in resp), f"Failed to buy ETH due to following error: {resp['message']}. BUY_ETH_GBP: {BUY_ETH_GBP}\n"
        logging.info("Successfully bought ETH")
        
        resp = auth_client.place_market_order(
            product_id="BTC-GBP", 
            side="buy",
            funds=BUY_BTC_GBP
        )
        assert("message" not in resp), f"Failed to buy BTC due to following error: {resp['message']}. BUY_BTC_GBP: {BUY_BTC_GBP}\n"
        logging.info("Successfully bought BTC")
        
        resp = auth_client.place_market_order(
            product_id="LTC-GBP", 
            side="buy",
            funds=BUY_LTC_GBP
        )
        assert("message" not in resp), f"Failed to buy LTC due to following error: {resp['message']}. BUY_LTC_GBP: {BUY_LTC_GBP}\n"
        logging.info("Successfully bought LTC")
    
        # Wait until LTC balance is available
        wait_counter = 0
        while (acc_dict["LTC"]["available"] == 0) and (wait_counter < 54):
            acc_dict = get_accounts(auth_client)
            time.sleep(5)
            wait_counter += 1
        assert(wait_counter < 54), "Took too long for LTC to become available to be used"
    
        # Send LTC to Kucoin address
        # WARNING: Sends ALL available LTC to KuCoin
        resp = auth_client.crypto_withdraw(
            amount=acc_dict["LTC"]["balance"],
            currency="LTC",
            crypto_address="MPB95foExUbNJ1n5TGn4VknJd5Trn2RUg4"
        )
        assert("message" not in resp), f"Failed to send LTC to KuCoin address due to following error: {resp['message']}\n"
        logging.info("Successfully withdrawn LTC to KuCoin address")
        
        # Log that the script finished successfully
        logging.info("Completed purchasing crypto from Coinbase Pro")
        
    # Log exceptions so they appear in CloudWatch
    except Exception as e:
        logging.exception("An error has occured in Coinbase pro auto-buy script")
        raise(e)
        
    return True
