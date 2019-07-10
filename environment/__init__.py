import os


def read_env(file_name='.env'):
    try:
        with open(file_name, 'r') as f:
            for line in f:
                parts = [x.strip() for x in line.split('=', 1)]
                if len(parts) < 2:
                    continue
                os.environ[parts[0]] = parts[1]
    except FileNotFoundError:
        pass

