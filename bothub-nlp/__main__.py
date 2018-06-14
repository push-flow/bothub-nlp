if __name__ == '__main__':
    import plac
    import sys
    from .cli import import_lang
    from .cli import import_langs
    from .cli import import_supported_languages
    from .cli import start

    commands = {
        'import_lang': import_lang,
        'import_langs': import_langs,
        'import_supported_languages': import_supported_languages,
        'start': start,
    }

    if len(sys.argv) == 1:
        print('Available commands: {}'.format(', '.join(commands)))
    else:
        command = sys.argv.pop(1)
        if command in commands:
            plac.call(commands[command], sys.argv[1:])
        else:
            print('Unknown command: {}'.format(command))
