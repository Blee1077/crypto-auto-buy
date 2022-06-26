"""Contains utility functions that are commonly used between lambda functions."""
import json
import boto3
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