import os

import pytest
import yaml

test_fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.mark.parametrize('template_file_path', [
    (
            'sam_stack_cf/template.yaml'
    ),
])
def test_process_cloudformation_resources(template_file_path):
    from commands.flatten import load_template

    template_path = os.path.abspath(os.path.join(test_fixtures, template_file_path))
    template_def = load_template(template_path)

    from commands.flatten import process_cloudformation_resources
    process_cloudformation_resources('root', template_def, {
        'master_template_location': template_path,
    })
