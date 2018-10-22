
import sys
import cfg

def eprint(*args, **kwargs):
    """ Helper function that prints on stderr. """
    print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    """ Helper function that prints when verbose has been enabled. """
    if cfg.args.v:
        print(*args, file=sys.stdout, **kwargs)
