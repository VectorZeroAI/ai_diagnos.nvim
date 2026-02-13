from pygls.lsp.server import LanguageServer
import threading

class AI_Diagnos_LSP_dummy(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}
        self.last_diagnostic_time = {}
        self.config = {}
        self.diagnostics_lock = threading.Lock()
