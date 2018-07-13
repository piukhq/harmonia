import click


def info(text):
    return click.style(text, fg='cyan')


@click.command()
def main():
    pass


if __name__ == '__main__':
    main()
