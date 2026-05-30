import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..', 'rootfs', 'opt', 'py-kms')
sys.path.insert(0, ROOT)

from tests.helpers import purge_pykms_modules
