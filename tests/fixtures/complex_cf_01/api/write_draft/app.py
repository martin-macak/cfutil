import os

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import utils as logging_utils
import shortuuid
import yaml

import json
from decimal import Decimal

from aws_lambda_powertools.utilities.validation import validator

boto3.set_stream_logger()
boto3.set_stream_logger("botocore")
logger = Logger()
logging_utils.copy_config_to_registered_loggers(source_logger=logger)

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'write_draft.schema.yaml')) as f:
    inbound_schema = yaml.load(f, Loader=yaml.FullLoader)

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'write_draft_response.schema.yaml')) as f:
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

    draft_id = event.get('DraftId')
    if draft_id is None:
        draft_id = generate_draft_id()
        record = create_new_draft(draft_id=draft_id,
                                  account_id=event['AccountId'],
                                  draft=event['Draft'])
    else:
        record = update_draft(draft_id=draft_id,
                              account_id=event['AccountId'],
                              draft=event['Draft'])

    return {
        'PK': record['PK'],
        'SK': record['SK'],
        'AccountId': record['AccountId'],
        'DraftId': record['SK'].split('#')[1],
        'Contract': record.get('Contract'),
        'PurchaseType': record.get('PurchaseType'),
        'ParentContractRef': record.get('ParentContractRef'),
    }


def create_new_draft(draft_id: str, account_id: str, draft: dict):
    purchase_type = draft.get('PurchaseType')
    parent_contract_ref_source = draft.get('ParentContractRef')
    parent_contract_ref = f'{parent_contract_ref_source["ContractId"]}/{parent_contract_ref_source["ContractVersion"]}' \
        if parent_contract_ref_source is not None \
        else None

    contract = json.loads(json.dumps(draft.get('Contract', {})), parse_float=Decimal)
    item = {
        'PK': f'ACCOUNT#{account_id}',
        'SK': f'DRAFT#{draft_id}',
        'OpenDraft': f'DRAFT#{draft_id}',
        'DraftId': draft_id,
        'AccountId': account_id,
        'PurchaseType': purchase_type,
        'ParentContractRef': parent_contract_ref,
        'Contract': contract,
    }

    drafts_table.put_item(
        Item=item,
        ConditionExpression='attribute_not_exists(PK) AND attribute_not_exists(SK)'
    )

    return item


def update_draft(draft_id: str, account_id: str, draft: dict):
    purchase_type = draft.get('PurchaseType')
    parent_contract_ref_source = draft.get('ParentContractRef')
    parent_contract_ref = f'{parent_contract_ref_source["ContractId"]}/{parent_contract_ref_source["ContractVersion"]}' \
        if parent_contract_ref_source is not None \
        else None

    contract = json.loads(json.dumps(draft.get('Contract', {})), parse_float=Decimal)
    deleted_contract_keys = [key for key in contract.keys() if contract[key] is None]
    changed_contract_keys = [key for key in contract.keys() if contract[key] is not None]

    contract_remove = ('REMOVE ' +
                       ','.join(map(lambda x: f'#contract.#contract_{x}', deleted_contract_keys))) \
        if len(deleted_contract_keys) > 0 else ''

    contract_update = (
            ', ' + ', '.join(map(lambda x: f'#contract.#contract_{x} = :contract_{x}', changed_contract_keys))) \
        if len(changed_contract_keys) > 0 else ''

    set_field_expression = f'SET #parent_contract_ref = :parent_contract_ref' \
                           f'  , #purchase_type = :purchase_type' \
                           f' {contract_update}'

    remove_expression = contract_remove

    update_expression = f'{set_field_expression} {remove_expression}'

    expression_attribute_values = {f':contract_{key}': contract[key] for key in changed_contract_keys}
    expression_attribute_values[':parent_contract_ref'] = parent_contract_ref
    expression_attribute_values[':purchase_type'] = purchase_type

    expression_attribute_names = {
                                     f'#contract_{key}': f'{key}' for key in changed_contract_keys + deleted_contract_keys
                                 } | {
                                     '#parent_contract_ref': 'ParentContractRef',
                                     '#purchase_type': 'PurchaseType',
                                     '#contract': 'Contract',
                                 }

    res = drafts_table.update_item(
        Key={
            'PK': f'ACCOUNT#{account_id}',
            'SK': f'DRAFT#{draft_id}'
        },
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames=expression_attribute_names,
        ReturnValues='ALL_NEW',
    )

    return res['Attributes']


def generate_draft_id():
    return shortuuid.random()
