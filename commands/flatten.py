import copy
import os
from typing import Union
from cfn.macros import rel_dir_path

import yaml

from cfn.cfn_yaml_tags import CloudFormationObject


def flatten_cloudformation_template(template_file_path: str) -> dict:
    pass


def process_cloudformation_resources(template_name: str,
                                     template: dict,
                                     context: dict) -> list:
    processed_resources = []

    template_resources: dict = template.get('Resources', {})
    for resource_name, resource_def in template_resources.items():
        if needs_flattening(resource_def):
            flattened_resources = flatten_resource(resource_name,
                                                   resource_def,
                                                   context)
            processed_resources.extend(flattened_resources)
        else:
            sanitized_resource = sanitize_resource(resource_name,
                                                   resource_def,
                                                   context)
            processed_resources.append(sanitized_resource)

    return processed_resources


def needs_flattening(resource_def: dict) -> bool:
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


def flatten_resource(resource_name: str,
                     resource_def: dict,
                     context: dict) -> list:
    resource_type = resource_def.get('Type', '')

    match resource_type:
        case 'AWS::CloudFormation::Stack':
            return flatten_nested_stack(resource_name,
                                        resource_def,
                                        context)
        case 'AWS::Serverless::Application':
            return flatten_serverless_application(resource_name,
                                                  resource_def,
                                                  context)
        case _:
            raise ValueError(f'Unknown resource type: {resource_type}')


def flatten_serverless_application(resource_name: str,
                                   resource_def: dict,
                                   context: dict) -> list:
    return flatten_nested_stack(resource_name, resource_def, context)


def flatten_nested_stack(resource_name: str,
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

    with rel_dir_path(os.path.dirname(nested_template_location)):
        nested_template_def = load_template(nested_template_location)

    nested_application_parameters = resource_properties.get('Parameters', {})

    nested_context = {
        'master_template_location': nested_template_location,
        'parameters': nested_application_parameters,
        'naming_prefix': get_naming_prefix(resource_name),
    }

    nested_resources = process_cloudformation_resources(resource_name,
                                                        nested_template_def,
                                                        nested_context)

    return nested_resources


def sanitize_resource(resource_name: str,
                      resource_def: dict,
                      context: dict) -> tuple[str, dict, dict]:
    naming_prefix = context.get('naming_prefix', '')

    sanitized_resource_name = f'{naming_prefix}{resource_name}'

    resource_properties = copy.deepcopy(resource_def.get('Properties', {}))

    def ref_from_context(key: str) -> tuple[bool, Union[str, None]]:
        parameters = context.get('parameters', {})
        if key in parameters:
            return True, parameters[key]
        else:
            return False, None

    def walk(obj: dict):
        for key, value in obj.items():
            match value:
                case CloudFormationObject(name='Ref'):
                    ref = value.data
                    is_ref_from_context, ref_value_from_context = ref_from_context(ref)
                    if is_ref_from_context:
                        effective_value = ref_value_from_context
                    else:
                        effective_value = value
                    obj[key] = effective_value
                case dict():
                    walk(value)
                case list():
                    for item in value:
                        walk(item)
                case _:
                    obj[key] = value

    walk(resource_properties)

    new_def = copy.deepcopy(resource_def)
    new_def['Properties'] = resource_properties

    return sanitized_resource_name, new_def, resource_def


def load_template(template_file_path: str) -> dict:
    from cfn.cfn_yaml_tags import CfnLoader

    with open(template_file_path, 'r') as template_file:
        template_def = yaml.load(template_file, Loader=CfnLoader)

    return template_def


def get_naming_prefix(resource_name: str) -> str:
    return resource_name
