import itertools
import os.path
import re
from io import IOBase
from typing import Union, Iterable, IO

import six
import yaml
from yaml import SafeLoader, SafeDumper
from yaml.constructor import ConstructorError

from cfn.macros import (include_json_string_from_yaml_file_constructor,
                        include_string_constructor,
                        generate_uuid_constructor,
                        rel_dir_path as macros_ref_dir)


class CloudFormationObject(object):
    SCALAR = 'scalar'
    SEQUENCE = 'sequence'
    SEQUENCE_OR_SCALAR = 'sequence_scalar'
    MAPPING = 'mapping'
    MAPPING_OR_SCALAR = 'mapping_scalar'

    name = None
    tag = None
    type = None
    macro = None

    def __init__(self, data):
        self.data = data

    def to_json(self):
        """Return the JSON equivalent"""

        def convert(obj):
            return obj.to_json() if isinstance(obj, CloudFormationObject) else obj

        if isinstance(self.data, dict):
            data = {key: convert(value) for key, value in six.iteritems(self.data)}
        elif isinstance(self.data, (list, tuple)):
            data = [convert(value) for value in self.data]
        else:
            data = self.data

        name = self.name

        if name == 'Fn::GetAtt' and isinstance(data, six.string_types):
            data = data.split('.')
        elif name == 'Ref' and '.' in data:
            name = 'Fn::GetAtt'
            data = data.split('.')

        return {name: data}

    @classmethod
    def construct(cls, loader, node):
        if isinstance(loader, CfnMacroLoader) and cls.macro is not None:
            return cls.macro(loader, node)

        if cls.type == cls.SCALAR:
            return cls(loader.construct_scalar(node))
        elif cls.type == cls.SEQUENCE:
            return cls(loader.construct_sequence(node))
        elif cls.type == cls.SEQUENCE_OR_SCALAR:
            try:
                return cls(loader.construct_sequence(node))
            except ConstructorError:
                return cls(loader.construct_scalar(node))
        elif cls.type == cls.MAPPING:
            return cls(loader.construct_mapping(node))
        elif cls.type == cls.MAPPING_OR_SCALAR:
            try:
                return cls(loader.construct_mapping(node))
            except ConstructorError:
                return cls(loader.construct_scalar(node))
        else:
            raise RuntimeError('Unknown type {}'.format(cls.type))

    @classmethod
    def represent(cls, dumper, obj):
        data = obj.data
        if isinstance(data, list):
            return dumper.represent_sequence(obj.tag, data)
        elif isinstance(data, dict):
            return dumper.represent_mapping(obj.tag, data)
        else:
            return dumper.represent_scalar(obj.tag, data)

    def __str__(self):
        return '{} {}'.format(self.tag, self.data)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.data))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.data == self.data


class CfnLoader(SafeLoader):
    pass


class CfnDumper(SafeDumper):
    pass


class CfnMacroLoader(CfnLoader):
    pass


_object_classes: Union[None, Iterable] = None

_ref = ('Ref', 'Ref', CloudFormationObject.SCALAR)

_functions = [
    ('Fn::And', 'And', CloudFormationObject.SEQUENCE),
    ('Fn::Condition', 'Condition', CloudFormationObject.SCALAR),
    ('Fn::Base64', 'Base64', CloudFormationObject.SCALAR),
    ('Fn::Equals', 'Equals', CloudFormationObject.SEQUENCE),
    ('Fn::FindInMap', 'FindInMap', CloudFormationObject.SEQUENCE),
    ('Fn::GetAtt', 'GetAtt', CloudFormationObject.SEQUENCE_OR_SCALAR),
    ('Fn::GetAZs', 'GetAZs', CloudFormationObject.SCALAR),
    ('Fn::If', 'If', CloudFormationObject.SEQUENCE),
    ('Fn::ImportValue', 'ImportValue', CloudFormationObject.SCALAR),
    ('Fn::Join', 'Join', CloudFormationObject.SEQUENCE),
    ('Fn::Not', 'Not', CloudFormationObject.SEQUENCE),
    ('Fn::Or', 'Or', CloudFormationObject.SEQUENCE),
    ('Fn::Select', 'Select', CloudFormationObject.SEQUENCE),
    ('Fn::Split', 'Split', CloudFormationObject.SEQUENCE),
    ('Fn::Sub', 'Sub', CloudFormationObject.SEQUENCE_OR_SCALAR),
]

_macros = [
    ('Macro::IncludeString', 'IncludeString', CloudFormationObject.SCALAR, include_string_constructor),
    ('Macro::IncludeJsonStringFromYamlFile', 'IncludeJsonStringFromYamlFile', CloudFormationObject.SCALAR,
     include_json_string_from_yaml_file_constructor),
    ('Macro::GenerateUUID', 'GenerateUUID', CloudFormationObject.SCALAR, generate_uuid_constructor),
]


def _init(safe=False):
    global _object_classes
    _object_classes = []
    for name_, tag_, type_, *args_ in itertools.chain(_functions, [_ref], _macros):
        if not tag_.startswith('!'):
            tag_ = '!{}'.format(tag_)
        tag_ = six.u(tag_)

        class Object(CloudFormationObject):
            name = name_
            tag = tag_
            type = type_
            macro = None if len(args_) == 0 else args_[0]

        obj_cls_name = re.search(r'\w+$', tag_).group(0)
        if six.PY2:
            obj_cls_name = str(obj_cls_name)
        Object.__name__ = obj_cls_name

        _object_classes.append(Object)
        globals()[obj_cls_name] = Object

        for loader in [CfnLoader, CfnMacroLoader]:
            loader.add_constructor(tag_, Object.construct)

        for dumper in [CfnDumper]:
            dumper.add_representer(Object, Object.represent)


def load_cfn(file: Union[str, IO], evaluate_macros=False) -> dict:
    if isinstance(file, str):
        with open(file, 'r') as f:
            return load_cfn(f, evaluate_macros=evaluate_macros)

    if not isinstance(file, IOBase):
        raise TypeError('file must be a file path or IO object')

    # noinspection PyUnresolvedReferences
    file_path = file.name
    loader_base = os.path.dirname(file_path)

    if evaluate_macros:
        with macros_ref_dir(loader_base):
            return yaml.load(file, Loader=CfnMacroLoader)
    else:
        return yaml.load(file, Loader=CfnLoader)


def dump_cfn(obj: dict) -> str:
    return yaml.dump(obj, Dumper=CfnDumper)


_init()
