import click


@click.option("-g", "--geography", is_flag=True)
def sync(geography):
    from airq.sync import models_sync

    models_sync(bool(geography))
