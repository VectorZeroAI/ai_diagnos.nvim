#!/usr/bin/env python3

import sqlite3
import threading
from typing import List
from lsprotocol import types

class CacheSystem:
    def __init__(self) -> None:
        raise NotImplementedError("Caching is not yet implemented")
        

    def get_cache(self, uri: str) -> None | List[types.Diagnostic]:
        raise NotImplementedError("Caching is not yet implemented")

    def cache_result(self, uri: str, diagnostics: List[types.Diagnostic] | types.Diagnostic):
        raise NotImplementedError("Caching is not yet implemented")

    def CachePrunerThread(self):
        raise NotImplementedError("Caching is not yet implemented")
