import time
import logging
from kucoin.client import Client
from utilities import load_json
logging.getLogger().setLevel(logging.INFO)

def truncate_float(n, places):
    return int(n * (10 ** places)) / 10 ** places
    

def lambda_handler(event, context):
    try:
        # Set up KuCoin client
        kucoin_secrets = load_json(event['secret_bucket'], event['kc_secret_key'])
        client = Client(kucoin_secrets['key'], kucoin_secrets['secret'], kucoin_secrets['passphrase'])
        
        # Log crypto ratio values and check ratios add to one
        logging.info(f"Ratio of TRAC to buy: {event['RATIO_TRAC']}")
        logging.info(f"Ratio of OPCT to buy: {event['RATIO_OPCT']}")
        assert((float(event['RATIO_TRAC']) + float(event['RATIO_OPCT'])) == 1), "Ratios don't sum to 1!\n"
            
        # Check LTC balance is not zero and is all available to use in the trade account
        LTC_acc = client.get_accounts('LTC', 'trade')[0]
        assert(float(LTC_acc['balance']) > 0), "No LTC in KuCoin trading account"
        assert(LTC_acc['balance'] == LTC_acc['available']), "Not all of LTC balance is available for trading\n"
    
        # Convert LTC to ETH
        LTC_precision = client.get_currency('LTC')['precision']
        LTC_funds = truncate_float(float(LTC_acc['balance']) / 1.001, LTC_precision-2)
        client.create_market_order(
            symbol='LTC-ETH',
            side=client.SIDE_SELL,
            size=LTC_funds
        )
        logging.info(f"Successfully converted LTC to ETH")
        
        # Wait until ETH balance is available to use
        wait_counter = 0
        ETH_acc = client.get_accounts('ETH', 'trade')[0]
        while (ETH_acc['available'] == 0) and (wait_counter < 24):
            time.sleep(5)
            ETH_acc = client.get_accounts('ETH', 'trade')[0]
            wait_counter += 1
        assert(wait_counter < 24), "Took too long for ETH to become available to be used\n"
        
        # Calculate how much to use to buy ETH and LTC, denominator takes into account the trading fee
        ETH_precision = client.get_currency('ETH')['precision']
        BUY_TRAC_ETH = (float(event["RATIO_TRAC"]) * float(ETH_acc['balance'])) / 1.001
        BUY_TRAC_ETH = truncate_float(BUY_TRAC_ETH, ETH_precision-2) # truncate to required precision
        BUY_OPCT_ETH = (float(event["RATIO_OPCT"]) * float(ETH_acc['balance'])) / 1.001
        BUY_OPCT_ETH = truncate_float(BUY_OPCT_ETH, ETH_precision-2)
        logging.info(f"Amount of ETH used to buy TRAC: {BUY_TRAC_ETH}")
        logging.info(f"Amount of ETH used to buy OPCT: {BUY_OPCT_ETH}")
        
        # Buy TRAC and OPCT with ETH
        client.create_market_order(
            symbol='TRAC-ETH',
            side=client.SIDE_BUY,
            funds=BUY_TRAC_ETH,
        )
        logging.info("Successfully bought TRAC")
        
        client.create_market_order(
            symbol='OPCT-ETH',
            side=client.SIDE_BUY,
            funds=BUY_OPCT_ETH,
        )
        logging.info("Successfully bought OPCT")
        
        # Wait 10 seconds for funds to appear
        time.sleep(15)
        
        # Transfer from trade wallet to main wallet for holding
        client.create_inner_transfer('OPCT', 'trade', 'main', float(client.get_accounts('OPCT', 'trade')[0]['balance']))
        client.create_inner_transfer('TRAC', 'trade', 'main', float(client.get_accounts('TRAC', 'trade')[0]['balance']))
        client.create_inner_transfer('LTC', 'trade', 'main', float(client.get_accounts('LTC', 'trade')[0]['balance']))
        logging.info("Successfully transferred OPCT and TRAC from trade to main wallet")
        
        # Log that the script successfully ran
        logging.info("Completed purchasing crypto from KuCoin")
        
    # Log exceptions so they appear in CloudWatch
    except Exception as e:
        logging.exception("An error has occured in KuCoin auto-buy script.")
        raise(e)
        
    return True
