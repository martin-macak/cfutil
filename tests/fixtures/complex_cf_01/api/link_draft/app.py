import os

import yaml
from aws_lambda_powertools.utilities.validation import validator

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'link_draft.schema.yaml')) as f:
    inbound_schema = yaml.load(f, Loader=yaml.FullLoader)

with open(os.path.join(os.path.dirname(__file__), 'schemas', 'link_draft_response.schema.yaml')) as f:
    outbound_schema = yaml.load(f, Loader=yaml.FullLoader)


@validator(inbound_schema=inbound_schema, outbound_schema=outbound_schema)
def lambda_handler(event, context):
    """
    This lambda accepts draft definition and replaces the old one.
    No partial updates.

    :param event:
    :param context:
    :return:
    """
    return {}
