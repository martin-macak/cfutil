import argparse
import copy
import os
import re
from typing import Union

from cfn.macros import rel_dir_path
from cfn.yaml_extensions import CloudFormationObject


def hook_command(parser, subparsers):
    def cmd(args):
        template = flatten_cloudformation_template(args.template,
                                                   evaluate_macros=args.macros)
        print(_dump_yaml(template))

    parser_flatten = subparsers.add_parser('flatten', help='flatten help')
    parser_flatten.add_argument('template', type=str, help='template file')
    parser_flatten.set_defaults(func=cmd)

    parser_flatten.add_argument('--macros',
                                action=argparse.BooleanOptionalAction,
                                help='evaluate macros')


def flatten_cloudformation_template(template_file_path: str, evaluate_macros=False) -> dict:
    template = _load_template(template_file_path, evaluate_macros=evaluate_macros)
    template_copy = copy.deepcopy(template)
    resources = process_cloudformation_resources('root', template_copy, {
        'master_template_location': template_file_path,
    })

    template_copy['Resources'] = {}

    for resource_name, resource_def, _ in resources:
        template_copy['Resources'][resource_name] = resource_def

    return template_copy


def _dump_yaml(template: dict) -> str:
    from cfn.yaml_extensions import dump_cfn
    return dump_cfn(template)


def process_cloudformation_resources(template_name: str,
                                     template: dict,
                                     context: dict) -> list:
    processed_resources = []

    template_resources: dict = template.get('Resources', {})
    for resource_name, resource_def in template_resources.items():
        if _needs_flattening(resource_def):
            flattened_resources = _flatten_resource(resource_name,
                                                    resource_def,
                                                    context)
            processed_resources.extend(flattened_resources)
        else:
            sanitized_resource = _sanitize_resource(resource_name,
                                                    resource_def,
                                                    context)
            processed_resources.append(sanitized_resource)

    return processed_resources


def _needs_flattening(resource_def: dict) -> bool:
    """
    This function checks whether current resource is a pointer to nested resource, that
    should be flattened.

    Currently only CloudFormation::Stack and Serverless::Application resources are supported
    if they refer to local files.

    :param resource_def: resource definition
    :return: True if resource_def is a pointer to nested resource, False otherwise
    """

    resource_type = resource_def.get('Type', '')
    resource_properties = resource_def.get('Properties', {})

    match resource_type:
        case 'AWS::CloudFormation::Stack':
            return resource_properties.get('Location', '').endswith('.yaml')
        case 'AWS::Serverless::Application':
            return resource_properties.get('Location', '').endswith('.yaml')
        case _:
            return False


def _flatten_resource(resource_name: str,
                      resource_def: dict,
                      context: dict) -> list:
    resource_type = resource_def.get('Type', '')

    match resource_type:
        case 'AWS::CloudFormation::Stack':
            return _flatten_nested_stack(resource_name,
                                         resource_def,
                                         context)
        case 'AWS::Serverless::Application':
            return _flatten_serverless_application(resource_name,
                                                   resource_def,
                                                   context)
        case _:
            raise ValueError(f'Unknown resource type: {resource_type}')


def _flatten_serverless_application(resource_name: str,
                                    resource_def: dict,
                                    context: dict) -> list:
    return _flatten_nested_stack(resource_name, resource_def, context)


def _flatten_nested_stack(resource_name: str,
                          resource_def: dict,
                          context: dict) -> list:
    master_template_location = context.get('master_template_location', None)
    if not master_template_location:
        raise ValueError('master_template_location is required when flattening nested Serverless::Application')

    resource_properties = resource_def.get('Properties', {})
    nested_application_location = resource_properties.get('Location', '')

    if not nested_application_location.endswith('.yaml'):
        raise ValueError(f'Nested application location should end with .yaml, got {nested_application_location}')

    nested_template_location = os.path.abspath(
        os.path.join(os.path.abspath(os.path.dirname(master_template_location)),
                     nested_application_location,
                     ))

    nested_template_def = _load_template(nested_template_location)

    nested_application_parameters = resource_properties.get('Parameters', {})

    nested_context = {
        'master_template_location': nested_template_location,
        'parameters': nested_application_parameters,
        'naming_prefix': _get_naming_prefix(resource_name),
    }

    nested_resources = process_cloudformation_resources(resource_name,
                                                        nested_template_def,
                                                        nested_context)

    return nested_resources


def _sanitize_resource(resource_name: str,
                       resource_def: dict,
                       context: dict) -> tuple[str, dict, dict]:
    naming_prefix = context.get('naming_prefix', '')

    sanitized_resource_name = f'{naming_prefix}{resource_name}'

    resource_properties = copy.deepcopy(resource_def.get('Properties', {}))

    def ref_from_param_context(key: str) -> tuple[bool, Union[str, None]]:
        parameters = context.get('parameters', {})
        if key in parameters:
            return True, parameters[key]
        else:
            return False, None

    def process_cfn_element(element):
        match element:
            case CloudFormationObject(name='Ref'):
                def process_ref():
                    ref = element.data
                    is_ref_from_context, ref_value_from_context = ref_from_param_context(ref)
                    if is_ref_from_context:
                        element.data = element.data
                    else:
                        element.data = f'{naming_prefix}{ref}'

                process_ref()
            case CloudFormationObject(name='Fn::Sub'):
                def process_sub():
                    sub_context = element.data[1] if isinstance(element.data, list) else {}
                    sub_expr = element.data[0] if isinstance(element.data, list) else str(element.data)

                    def ref_pointer_from_context(key: str, local_context: dict) -> tuple[bool, Union[str, None]]:
                        if key in local_context:
                            return True, key
                        else:
                            return False, None

                    pm = None
                    retargeted_sub_expr = ''
                    for m in re.finditer(r'(?<!\\)\$\{[a-zA-Z_.]+}', sub_expr):
                        expr = sub_expr[m.start() + 2:m.end() - 1]
                        pointer, *rest = expr.split('.', 1)
                        is_pointer_from_sub_context, ref_pointer_from_sub_context = ref_pointer_from_context(pointer, sub_context)
                        is_pointer_from_param_context, ref_pointer_from_param_context = ref_pointer_from_context(pointer, context)
                        if is_pointer_from_sub_context:
                            retargeted_pointer = ref_pointer_from_sub_context
                        elif is_pointer_from_param_context:
                            retargeted_pointer = ref_pointer_from_param_context
                        else:
                            retargeted_pointer = f'{naming_prefix}{pointer}'

                        retargeted_expr = '.'.join([retargeted_pointer, *rest])
                        retargeted_sub_expr += sub_expr[pm.end() if pm is not None else 0:m.start()] + '${' + retargeted_expr + '}'
                        pm = m

                    _walk_dict(sub_context)

                process_sub()
            case CloudFormationObject(name='Fn::GetAtt'):
                def process_get_att():
                    pointer = element.data
                    target_resource_name, attr_name = pointer.split('.')
                    is_ref_from_context, ref_value_from_context = ref_from_param_context(target_resource_name)
                    element.data = f'{naming_prefix}{ref_value_from_context}.{attr_name}'

                process_get_att()

    def _walk_dict(obj: dict):
        for key, value in obj.items():
            match value:
                case CloudFormationObject():
                    process_cfn_element(element=value)
                case dict():
                    _walk_dict(value)
                case list():
                    _walk_list(value)

    def _walk_list(obj: list):
        for member in obj:
            match member:
                case dict():
                    _walk_dict(member)
                case list():
                    _walk_list(member)
                case CloudFormationObject():
                    process_cfn_element(element=member)

    _walk_dict(resource_properties)

    new_def = copy.deepcopy(resource_def)
    new_def['Properties'] = resource_properties

    return sanitized_resource_name, new_def, resource_def


def _load_template(template_file_path: str, evaluate_macros: bool = False) -> dict:
    from cfn.yaml_extensions import load_cfn

    with rel_dir_path(os.path.dirname(template_file_path)):
        with open(template_file_path, 'r') as template_file:
            template_def = load_cfn(template_file, evaluate_macros=evaluate_macros)

    return template_def


def _get_naming_prefix(resource_name: str) -> str:
    return resource_name
