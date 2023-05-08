import os

import pytest

test_fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.mark.parametrize('template_file_path, expected', [
    (
            'sam_stack_cf/template.yaml',
            None,
    ),
])
def test_process_cloudformation_resources(template_file_path, expected):
    from commands.flatten import _load_template

    template_path = os.path.abspath(os.path.join(test_fixtures, template_file_path))
    template_def = _load_template(template_path)

    from commands.flatten import process_cloudformation_resources
    got = process_cloudformation_resources('root', template_def, {
        'master_template_location': template_path,
    })

    if expected is not None:
        assert got == expected

@pytest.mark.parametrize('template_file_path, expected', [
    (
            'sam_stack_cf/template.yaml',
            None,
    ),
])
def test_flatten_cloudformation_template(template_file_path, expected):
    template_path = os.path.abspath(os.path.join(test_fixtures, template_file_path))

    from commands.flatten import flatten_cloudformation_template
    got = flatten_cloudformation_template(template_path)

    if expected is not None:
        assert got == expected

@pytest.mark.parametrize('template_file_path, expected', [
    (
            'sam_stack_cf/template.yaml',
            None,
    ),
])
def test_dump_yaml(template_file_path, expected):
    template_path = os.path.abspath(os.path.join(test_fixtures, template_file_path))

    from commands.flatten import _dump_yaml, flatten_cloudformation_template
    processed = flatten_cloudformation_template(template_path)
    got = _dump_yaml(processed)

    if expected is not None:
        assert got == expected
