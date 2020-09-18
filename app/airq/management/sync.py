import click


@click.option("-g", "--geography", is_flag=True)
@click.option("-e", "--only-if-empty", is_flag=True)
def sync(geography, only_if_empty):
    from airq.sync import models_sync

    models_sync(bool(geography), bool(only_if_empty))
