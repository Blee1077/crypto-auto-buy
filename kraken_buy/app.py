import os
import json
import time
import boto3
import logging
import krakenex
from pykrakenapi import KrakenAPI

logging.getLogger().setLevel(logging.INFO)
s3 = boto3.resource('s3')

def load_json(bucket: str, key: str) -> dict:
    """Loads a JSON file from S3 bucket.
    
    Args:
        bucket (str): S3 bucket containing JSON file
        key (str): Path within bucket of JSON file
        
    Returns:
        dict
    """
    content_object = s3.Object(bucket, key)
    file_content = content_object.get()["Body"].read().decode("utf-8")
    return json.loads(file_content)


def truncate_float(n: float, places: int):
    return int(n * (10 ** places)) / 10 ** places


def lambda_handler(event, context):
    try:
        # Load in Kraken secrets and create authenticated client
        kraken_secrets = load_json(os.environ['SECRET_BUCKET'], os.environ['KRAKEN_SECRET_KEY'])
        api = krakenex.API(kraken_secrets['key'], kraken_secrets['secret_key'])
        client = KrakenAPI(api)
        
        # Log environment variables
        logging.info(f"Total monthly buy funds: £{os.environ['MONTHLY_FUND']}")
        logging.info(f"Buy frequency per month: {os.environ['MONTHLY_FREQ']}")
        logging.info(f"Ratio of ETH to buy: {os.environ['RATIO_ETH']}")
        logging.info(f"Ratio of BTC to buy: {os.environ['RATIO_BTC']}")
        
        # Calculate how much to use to buy ETH and BTC
        BUY_GBP = int(os.environ['MONTHLY_FUND']) / int(os.environ['MONTHLY_FREQ'])
        BUY_ETH_GBP = BUY_GBP * float(os.environ['RATIO_ETH'])
        BUY_BTC_GBP = BUY_GBP * float(os.environ['RATIO_BTC'])
        logging.info(f"GBP funds to use for this run: £{BUY_GBP}")
        logging.info(f"Amount of ETH to buy in GBP: £{BUY_ETH_GBP}")
        logging.info(f"Amount of BTC to buy in GBP: £{BUY_BTC_GBP}")
        
        # Trading pair names
        BTCGBP_PAIR = "BTCGBP"
        ETHGBP_PAIR = "ETHGBP"
    
        # Check there's enough money GBP in account to buy
        balance_df = client.get_account_balance()
        assert balance_df.loc['ZGBP']['vol'] >= BUY_GBP, "Not enough GBP to buy crypto!"
        
        ETH_PRICE, _ = client.get_ohlc_data(pair=ETHGBP_PAIR)
        BTC_PRICE, _ = client.get_ohlc_data(pair=BTCGBP_PAIR)
        ETH_BUY_AMT = truncate_float(BUY_ETH_GBP/ETH_PRICE.iloc[0]['open'], places=8)
        BTC_BUY_AMT = truncate_float(BUY_BTC_GBP/BTC_PRICE.iloc[0]['open'], places=8)
    
        # Buy ETH and BTC
        try:
            client.add_standard_order(ordertype='market', type='buy', pair=ETHGBP_PAIR, volume=ETH_BUY_AMT, validate=False)
            logging.info("Successfully bought ETH")
        except Exception as e:
            logging.error(f"Failed to buy ETH due to following error: {str(e)}. BUY_ETH_GBP: {BUY_ETH_GBP}, ETH_BUY_AMT: {ETH_BUY_AMT}\n")
            raise e
        
        try:
            client.add_standard_order(ordertype='market', type='buy', pair=BTCGBP_PAIR, volume=BTC_BUY_AMT, validate=False)
            logging.info("Successfully bought BTC")
        except Exception as e:
            logging.error(f"Failed to buy BTC due to following error: {str(e)}. BUY_BTC_GBP: {BUY_BTC_GBP}, BTC_BUY_AMT: {BTC_BUY_AMT}\n")
            raise e
        
        # Log that the script purchased successfully
        logging.info("Completed purchasing BTC and ETH from Kraken")
        time.sleep(20)
        
        # Check if withdrawal requirements are met
        ETH_BAL = balance_df.loc['XETH']['vol']
        BTC_BAL = balance_df.loc['XXBT']['vol']
        
        # Withdrawal fee for ETH is 0.0035 which is ~£5 as of 2023/02/03 -> expensive to withdraw
        if ETH_BAL * ETH_PRICE >= float(os.environ['ETH_WITHDRAW_THRESH']):
            try:
                client.withdraw_funds('ETH Ledger Nano S+', asset='XETH', amount=ETH_BAL)
                logging.info(f"Successfully withdrew {ETH_BAL} ETH to cold wallet")
            except Exception as e:
                logging.error(f"Failed to withdraw ETH due to following error: {str(e)}.")
                raise e
        else:
            logging.info(f"ETH balance has not hit threshold to withdraw.")
        
        # Withdrawal fee for BTC is 0.00001 which is £0.19 as of 2023/02/03 -> cheap to withdraw
        if BTC_BAL * BTC_PRICE >= float(os.environ['BTC_WITHDRAW_THRESH']):
            try:
                client.withdraw_funds('BTC Ledger Nano S+', asset='XXBT', amount=BTC_BAL)
                logging.info(f"Successfully withdrew {BTC_BAL} BTC to cold wallet")
            except Exception as e:
                logging.error(f"Failed to withdraw BTC due to following error: {str(e)}.")
                raise e
        else:
            logging.info(f"BTC balance has not hit threshold to withdraw.")
        
    # Log exceptions so they appear in CloudWatch
    except Exception as e:
        logging.exception("An error has occured in Kraken auto-buy script")
        raise e
        
    return True
