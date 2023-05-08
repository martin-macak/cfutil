import os

import boto3
import yaml
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import utils as logging_utils
from aws_lambda_powertools.utilities.validation import validator

boto3.set_stream_logger()
boto3.set_stream_logger("botocore")
logger = Logger()
logging_utils.copy_config_to_registered_loggers(source_logger=logger)

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'delete_draft.schema.yaml')) as f:
    inbound_schema = yaml.load(f, Loader=yaml.FullLoader)

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'delete_draft_response.schema.yaml')) as f:
    outbound_schema = yaml.load(f, Loader=yaml.FullLoader)

dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource(service_name='dynamodb')

DRAFTS_TABLE_NAME = os.environ['DRAFTS_TABLE_NAME']

drafts_table = dynamodb.Table(DRAFTS_TABLE_NAME)


@validator(inbound_schema=inbound_schema, outbound_schema=outbound_schema)
def lambda_handler(event, context):
    """
    This lambda accepts draft definition and replaces the old one.
    No partial updates.

    :param event:
    :param context:
    :return:
    """

    account_id = event['AccountId']
    draft_id = event['DraftId']

    db_record = delete_draft(account_id=account_id, draft_id=draft_id)
    return db_record


def delete_draft(account_id, draft_id):
    res = drafts_table.delete_item(
        Key={
            'PK': f'ACCOUNT#{account_id}',
            'SK': f'DRAFT#{draft_id}'
        },
        ReturnValues='ALL_OLD',
    )

    return res.get('Attributes')