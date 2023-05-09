import os

import pytest


@pytest.mark.parametrize('template_file_path, evaluate_macros, expected', [
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'simple_cf', 'template.yaml')),
            True,
            None,
    ),
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'complex_cf_01', 'template.yaml')),
            True,
            None,
    ),
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'simple_cf', 'template.yaml')),
            False,
            None,
    ),
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'complex_cf_01', 'template.yaml')),
            False,
            None,
    ),
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'with_macros_01', 'template.yaml')),
            True,
            None,
    ),
    (
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'with_macros_01', 'template.yaml')),
            False,
            None,
    ),
])
def test_load_cfn(template_file_path, evaluate_macros, expected):
    from cfn.yaml_extensions import load_cfn
    got = load_cfn(template_file_path, evaluate_macros=evaluate_macros)

    from cfn.yaml_extensions import dump_cfn
    yaml_image = dump_cfn(got)
    print(yaml_image)

    if expected is not None:
        assert got == expected
