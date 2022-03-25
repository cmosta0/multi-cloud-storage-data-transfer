import logging
import os
from datetime import datetime

import boto3
from google.cloud import storage


def _get_logger():
    logger = logging.getLogger('multi_cloud_data_transfer')
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)
    return logger


_logger = _get_logger()


SESSION = boto3.Session(
    aws_access_key_id=os.environ['AWS_SERVICE_ACCESS_KEY'].strip(),
    aws_secret_access_key=os.environ['AWS_SERVICE_SECRET'].strip(),
)
AWS_REGION = os.environ['AWS_REGION']
S3 = SESSION.resource('s3', region_name=AWS_REGION)
S3_CLIENT = SESSION.client('s3', region_name=AWS_REGION)
STORAGE_CLIENT = storage.Client(project=os.environ['GCP_PROJECT_NAME'])

S3_BUCKET = S3.Bucket(os.environ['S3_BUCKET'])
GCS_BUCKET = STORAGE_CLIENT.get_bucket(os.environ['GCS_BUCKET'])



def _get_prefix_path(prefix=None, given_date=None):
    # if given_date is none it will take current date as the default value
    date_path = given_date if given_date else datetime.today().strftime('%Y/%m/%d')
    prefix = f'{prefix}/' if prefix else ''
    return f"{prefix}{date_path}/"


def _transfer_file(file_key):
    s3_response_object = S3_CLIENT.get_object(Bucket=os.environ['S3_BUCKET'], Key=file_key)
    blob = GCS_BUCKET.blob(file_key)
    blob.upload_from_string(s3_response_object["Body"].read())
    _logger.info(f'transfer completed for {file_key}')


def transfer_from_s3_to_gcs(prefix=None, given_date=None):
    _logger.info(f'Starting process for prefix: {prefix} and given date: {given_date}')
    prefix_path = _get_prefix_path(prefix=prefix, given_date=given_date)
    _logger.info(f'Extract objects from {S3_BUCKET} - prefix: {prefix_path}')
    for s3_object in S3_BUCKET.objects.filter(Prefix=prefix_path):
        _transfer_file(file_key=s3_object.key)


def data_transfer_handler(e, _):
    attributes = e['attributes']
    transfer_from_s3_to_gcs(prefix=attributes['DATA_PREFIX'], given_date=attributes.get('DATA_TRANSFER_DATE', None))
