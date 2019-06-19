from __future__ import print_function
from sys import getsizeof, stderr
from itertools import chain
from collections import deque
try:
    from reprlib import repr
except ImportError:
    pass

import base64
import json
import numpy as np
import zlib


def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                    }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


def json_to_b64(seg_res):
    serial_seg_res = {
        'seg_map': seg_res['seg_map'].tolist(),
        'color_map': (
            seg_res['color_map'][0].tolist(),
            seg_res['color_map'][1].tolist(),
        )
    }
    compressed_data = zlib.compress(json.dumps(serial_seg_res).encode('utf-8'))

    try:
        import pybase64
        data_64 = pybase64.b64encode(compressed_data, validate=True
                                     ).decode('ascii')
    except ImportError:
        data_64 = base64.b64encode(compressed_data).decode('ascii')
    return data_64


def b64_to_json(data_64):
    try:
        import pybase64
        decoded_data = pybase64.b64decode(data_64, validate=True)
    except ImportError:
        decoded_data = base64.b64decode(data_64)

    serial_seg_res = json.loads(
        zlib.decompress(decoded_data)
    )

    seg_res = {
        'seg_map': np.array(serial_seg_res['seg_map'], dtype=int),
        'color_map': (
            np.array(serial_seg_res['color_map'][0]),
            np.array(serial_seg_res['color_map'][1])
        )
    }
    return seg_res
