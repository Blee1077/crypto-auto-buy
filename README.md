# Cryptocurrency Auto-buy Application
[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/designed-in-etch-a-sketch.svg)](https://forthebadge.com)

The purpose of this project is to create an AWS-based serverless application that purchases a pre-defined set of cryptocurrencies based on a user-defined frequency period and a user-defined amount. The core functionality is an AWS Step Function that runs AWS Lambda functions in a sequence and is scheduled to run on a user-defined frequency using an EventBridge rule, AWS SAM is used to create all the necessary AWS resources to get this application up and running. In the event that the state machine fails, an alarm will be sent to the email used to set up SNS notifications.

Currently the application takes a three-step approach which utilises two exchanges. The first step is to buy blue-chip (i.e., Bitcoin and Ethereum) cryptocurrencies on Coinbase Pro due to its low trading fees and user-friendly fiat on-ramp process. In addition, Litecoin is also purchased which is then sent to a wallet on the KuCoin exchange. The second step is to check that the Litecoin has been successfully transferred to KuCoin, if not then check again until it is.
The third and final step is to then utilise the transferred Litecoin to purchase alt-coins which aren't available on Coinbase.

This project contains source code and supporting files for the serverless application that you can deploy with the SAM CLI. It includes the following files and folders:

- functions - Code for the application's Lambda functions purchase cryptocurrencies on exchanges or check that funds have been transferred.
- statemachines - Definition for the state machine that orchestrates the cryptocurrency purchasing workflow.
- util_layer - Utility functions that are shared across Lambda functions.
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including Step Functions state machines, Lambda functions and an EventBridge rule trigger. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Pre-requisites

1. An AWS account
2. SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
3. Python 3 - [Install Python 3](https://www.python.org/downloads/)
4. Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)
5. A JSON file named `"cbpro-api-secret.json"` containing your Coinbase Pro API key details ([instructions here to create API key](https://help.coinbase.com/en/pro/other-topics/api/how-do-i-create-an-api-key-for-coinbase-pro)) with the following structure:

    ```yaml
    {
        "secret": PUT_SECRET_HERE
        "key": PUT_KEY_HERE
        "passphrase": PUT_PASSPHRASE_HERE
    }
    ```
6. A JSON file named `"kucoin-api-secret.json"` containing your KuCoin API key details ([instructions here to create API key](https://www.kucoin.com/support/360015102174-How-to-Create-an-API)) with the following structure:

    ```yaml
    {
        "secret": PUT_SECRET_HERE
        "key": PUT_KEY_HERE
        "passphrase": PUT_PASSPHRASE_HERE
    }
    ```


## Configurations

The `template.yaml` contains the following user-defined global environment variables:

- COINBASE_SECRET_KEY - The filename of the JSON file which contains your Coinbase Pro API key, the structure of which is defined in the pre-requisites section above, set to `"cbpro-api-secret.json"` by default.
- KUCOIN_SECRET_KEY - The filename of the JSON file which contains your KuCoin API key, the structure of which is defined in the pre-requisites section above, set to `"kucoin-api-secret.json"` by default.
- MONTHLY_FREQ - How many times to buy in a month, set to `2` by default.
- MONTHLY_FUND - How much in £ to invest per month, set to `400` by default
- RATIO_BTC - Proportion of MONTHLY_FUND to invest in Bitcoin (BTC), set to `0.425` by default.
- RATIO_ETH - Proportion of MONTHLY_FUND to invest in Ethereum (ETH), set to `0.425` by default.
- RATIO_OPCT - Proportion of (1 - RATIO_BTC - RATIO_ETH) * MONTHLY_FUND to invest in Opacity (OPCT), set to `0.1` by default.
- RATIO_TRAC - Proportion of (1 - RATIO_BTC - RATIO_ETH) * MONTHLY_FUND to invest in Origin Trail (TRAC), set to `0.9` by default.

## Use the SAM CLI to build locally

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

Build this application with the `sam build --use-container` command. The `use-container` option makes it so that the build happens inside a Lambda-like container.

```bash
sam build --use-container
```

For each of the Lambda functions, the SAM CLI installs dependencies defined in `requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

## Deploy the application

To deploy the application for the first time, run the following command in your shell after building:

```bash
sam deploy --guided
```

This command will package and deploy this application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching this project's function.
* **AWS Region**: The AWS region you want to deploy this app to.
* **SNS Email Parameter**: The email address to send execution failure notifications.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this one, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to this application.

## Post-deployment

After deploying the application, all the AWS resources defined in the `template.yaml` file will be made in your AWS account. Go to the created S3 bucket and upload both the JSON files containing Coinbase Pro and KuCoin API key details. 

## Cleanup

To delete the deployed application, use the AWS CLI. Assuming you used this project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name crypto-auto-buy
```
