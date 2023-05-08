def test_run_flatten():
    args = 'test flatten fixtures/sam_stack_cf/template.yaml'
    from app.cli import run
    run(*args.split(' '))


def test_run_retain():
    args = 'test retain fixtures/sam_stack_cf/template.yaml'
    from app.cli import run
    run(*args.split(' '))
