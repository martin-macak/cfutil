import json
import os
import uuid
from contextlib import contextmanager

import yaml

_include_rel_dir = os.curdir
_rel_dir_stack = []


def load_file(file_name):
    if os.path.isabs(file_name):
        with open(file_name, "r") as f:
            return f.read(file_name)
    else:
        with open(os.path.join(_include_rel_dir, file_name), "r") as f:
            return f.read()


def include_string_constructor(
        loader_context: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> str:
    file_path = loader_context.construct_scalar(node)
    return load_file(file_path)


def include_json_string_from_yaml_file_constructor(
        loader_context: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> str:
    file_path = loader_context.construct_scalar(node)
    raw = load_file(file_path)
    yaml_content = yaml.load(raw, Loader=yaml.SafeLoader)

    return json.dumps(yaml_content)


def generate_uuid_constructor(
        loader_context: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> str:
    return str(uuid.uuid4())


def change_rel_dir(new_dir):
    global _include_rel_dir
    _include_rel_dir = new_dir


def push_rel_dir(new_dir):
    global _rel_dir_stack
    global _include_rel_dir
    _rel_dir_stack.append(new_dir)
    _include_rel_dir = new_dir


def pop_rel_dir():
    global _rel_dir_stack
    global _include_rel_dir
    _include_rel_dir = _rel_dir_stack.pop()
    return _include_rel_dir


@contextmanager
def rel_dir_path(new_dir):
    push_rel_dir(new_dir)
    yield
    pop_rel_dir()
