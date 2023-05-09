import argparse
import copy
import os

from cfn.macros import rel_dir_path


def hook_command(parser, subparsers):
    def cmd(args):
        template = _process_template(args.template, evaluate_macros=args.macros)
        print(_dump_yaml(template))

    parser_flatten = subparsers.add_parser('retain', help='retain help')
    parser_flatten.add_argument('template', type=str, help='template file')
    parser_flatten.set_defaults(func=cmd)

    parser_flatten.add_argument('--macros',
                                action=argparse.BooleanOptionalAction,
                                help='evaluate macros')


def _dump_yaml(template: dict) -> str:
    from cfn.yaml_extensions import dump_cfn
    return dump_cfn(template)


def _process_template(template_path: str, evaluate_macros: bool = False) -> dict:
    template = _load_template(template_path, evaluate_macros=evaluate_macros)
    return _mark_resources_as_retained(template)


def _mark_resources_as_retained(template: dict) -> dict:
    template_copy = copy.deepcopy(template)

    for resource_name, resource_def in template_copy.get('Resources', {}).items():
        if _is_stateful_resource(resource_def):
            resource_def['DeletionPolicy'] = 'Retain'

    return template_copy


def _load_template(template_file_path: str, evaluate_macros: bool = False) -> dict:
    from cfn.yaml_extensions import load_cfn

    with rel_dir_path(os.path.dirname(template_file_path)):
        with open(template_file_path, 'r') as template_file:
            template_def = load_cfn(template_file, evaluate_macros=evaluate_macros)

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
