import copy
import os

import yaml

from cfn.macros import rel_dir_path


def hook_command(parser, subparsers):
    def cmd(args):
        template = _process_template(args.template)
        print(_dump_yaml(template))

    parser_flatten = subparsers.add_parser('retain', help='retain help')
    parser_flatten.add_argument('template', type=str, help='template file')
    parser_flatten.set_defaults(func=cmd)


def _dump_yaml(template: dict) -> str:
    from cfn.cfn_yaml_tags import CfnDumper
    return yaml.dump(template, Dumper=CfnDumper)


def _process_template(template_path: str) -> dict:
    template = _load_template(template_path)
    return _mark_resources_as_retained(template)


def _mark_resources_as_retained(template: dict) -> dict:
    template_copy = copy.deepcopy(template)

    for resource_name, resource_def in template_copy.get('Resources', {}).items():
        if _is_stateful_resource(resource_def):
            resource_def['DeletionPolicy'] = 'Retain'

    return template_copy


def _load_template(template_file_path: str) -> dict:
    from cfn.cfn_yaml_tags import CfnLoader

    with rel_dir_path(os.path.dirname(template_file_path)):
        with open(template_file_path, 'r') as template_file:
            template_def = yaml.load(template_file, Loader=CfnLoader)

    return template_def


def _is_stateful_resource(resource_def: dict):
    return [
        'AWS::DynamoDB::Table',
        'AWS::Cognito::UserPool',
        'AWS::Cognito::IdentityPool',
        'AWS::S3::Bucket',
        'AWS::Glue::Database',
        'AWS::Glue::Table',
        'AWS::SQS::Queue',
        'AWS::Kinesis::Stream',
    ].__contains__(resource_def.get('Type'))
