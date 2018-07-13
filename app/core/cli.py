import click

from app.core.import_director import ImportDirector


def info(text):
    return click.style(text, fg='cyan')


@click.group()
def cli():
    pass


@cli.command()
def import_director():
    director = ImportDirector()

    try:
        director.enter_loop()
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


if __name__ == '__main__':
    cli()
