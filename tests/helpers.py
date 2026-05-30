import sys


def purge_pykms_modules():
    for name in list(sys.modules):
        if name.startswith('pykms_'):
            del sys.modules[name]
