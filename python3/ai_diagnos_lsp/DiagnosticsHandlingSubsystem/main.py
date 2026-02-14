#!/usr/bin/env python3

from __future__ import annotations
import sqlite3
import threading
from typing import TYPE_CHECKING
import time
import logging
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from lsprotocol import types

from ai_diagnos_lsp.analysers.chains.GeneralDiagnosticsPydanticOutputParser import GeneralDiagnosticsPydanticObjekt

if TYPE_CHECKING:
    from ai_diagnos_lsp.AIDiagnosLSPClass import AIDiagnosLSP

from ai_diagnos_lsp.DiagnosticsHandlingSubsystem.Converters.GeneralDiagnosticsPydanticToLSProtocol import GeneralDiagnosticsPydanticToLSProtocol

class DiagnosticsHandlingSubsystemClass:
    """
    My own internal subsyste for handling many different internal types of diagnostics,
    as well as diagnostics saving and reusal. 
    
    Will propably get its own directory once actually implemented. 
    """

    SUPPORTED_DIAGNOSTIC_TYPES = ["Basic", "CrossFile", "Logic", "Style", "Security", "Deep"]

    def __init__(self,
                 ls: AIDiagnosLSP,
                 sqlite_db_name,
                 ttl_seconds_until_deletion,
                 ttl_seconds_until_invalidation
                 ) -> None:
        self.ls = ls
        self.ttl_seconds_until_deletion = ttl_seconds_until_deletion
        self.db_lock = threading.Lock()
        self.ttl_seconds_until_invalidation = ttl_seconds_until_invalidation

        threading.Thread(target=self.TTLBasedDeletionThread, daemon=True).start()
        threading.Thread(target=self.TTLBasedDiagnosticsInvalidationThread, daemon=True).start()
        
        self.conn = sqlite3.connect(sqlite_db_name, autocommit=True, check_same_thread=False)
        curr = self.conn.cursor()

        # SQL DB initialisation

        curr.execute("""
        CREATE TABLE IF NOT EXISTS files(
            uri TEXT PRIMARY KEY,
            last_changed_at REAL NOT NULL
            )
                          """)
        # TODO: Add hash based renaming detection. 

        curr.executescript("""
                           PRAGMA journal_mode=WAL;
                           PRAGMA synchronous=NORMAL;
                           PRAGMA cache_size=-64000;
                           PRAGMA temp_store=MEMORY;
                           PRAGMA mmap_size=268435456;
                           PRAGMA foreign_keys=ON;
                           """)

        for name in self.SUPPORTED_DIAGNOSTIC_TYPES:
            curr.execute(f"""
            CREATE TABLE IF NOT EXISTS diagnostics_{name}(
                uri TEXT NOT NULL,
                diagnostics TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (uri) REFERENCES files ON DELETE CASCADE
                )
                              """, )
        
        VIEW_CREATION_SCRIPT = """
        CREATE VIEW IF NOT EXISTS all_diagnostics_view AS \n
        """
        for name in self.SUPPORTED_DIAGNOSTIC_TYPES:
            VIEW_CREATION_SCRIPT = VIEW_CREATION_SCRIPT + f"SELECT uri, '{name}' AS diagnostics_type, diagnostics, created_at FROM diagnostics_{name} \n \n"
            if self.SUPPORTED_DIAGNOSTIC_TYPES.index(name) != len(self.SUPPORTED_DIAGNOSTIC_TYPES) - 1:
                VIEW_CREATION_SCRIPT = VIEW_CREATION_SCRIPT + "UNION ALL \n"

        curr.execute(VIEW_CREATION_SCRIPT)

        curr.close()

    def register_file_write(self, document_uri: str):
        curr = self.conn.cursor()
        try:
            tmp = curr.execute("""
            SELECT uri FROM files WHERE uri = ?
                                    """, (document_uri,)).fetchall()

            if len(tmp) > 0:
                with self.db_lock:
                    curr.execute("""
                    UPDATE files SET last_changed_at = ? WHERE uri = ?
                                      """, (time.time(), document_uri))
            else:
                with self.db_lock:
                    curr.execute("""
                    INSERT INTO files(uri, last_changed_at) VALUES (?, ?)
                                      """, (time.time(), document_uri))
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"register file write encoutered the following error: {e}")
            raise Exception(f"register file write encoutered the following exeption: {e}") from e
        finally:
            curr.close()


    def save_new_diagnostic(self, diagnostics: GeneralDiagnosticsPydanticObjekt, document_uri: str, analysis_type: str) -> bool:
        """
        Registers the diagnostic to the DataBase. DOES NOT PUBLISH THEM TO THE CLIENT
        """
        curr = self.conn.cursor()
        try:
            with self.db_lock:
                curr.execute(f"""
                INSERT INTO diagnostics_{analysis_type}(uri, diagnostics, created_at) VALUES(?, ?, ?)
                                  """, (document_uri, diagnostics.model_dump_json(), time.time()))
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt register new diagnosic due to following error: {e}")
            return False
        else:
            self.ls.workspace_diagnostic_refresh(None)
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.info("sucsessfully registered new diagnostics")
            return True
        finally:
            curr.close()


    def load_all_diagnostics(self):
        """
        Directly publishes all the diagnostics that it can find. 
        """
        curr = self.conn.cursor()
        try:
            all_diagnostics_for_every_file = curr.execute("""
            SELECT diagnostics, uri FROM all_diagnostics_view
                                                              """).fetchall()
            
            diagnostics_sorted_per_file = {}

            for i in all_diagnostics_for_every_file:
                current_uri = i[1]
                diagnostics = i[0]
                previous = diagnostics_sorted_per_file.get(current_uri)
                if previous is None:
                    previous = []
                new_list = previous
                new_list.append(diagnostics)
                diagnostics_sorted_per_file[current_uri] = new_list

            diagnostics_per_file = {}

            for i in diagnostics_sorted_per_file.items():
                pydantic_objekts_list = []
                for j in i[1]:
                    pydantic_objekts_list.append(GeneralDiagnosticsPydanticObjekt.model_validate_json(j))

                diagnostics_per_file[i[0]] = pydantic_objekts_list

            for i in diagnostics_per_file.items():
                document = Path(unquote(urlparse(i[0]).path)).read_text()
                converted_to_lsp_format = GeneralDiagnosticsPydanticToLSProtocol(self.ls, i[1], document)               
                self.ls.diagnostics[i[0]] = converted_to_lsp_format

        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt load diagnostics due to following error : {e}")
            return False
        finally:
            curr.close()
                



    def load_diagnostics_for_file(self, document_uri: str) -> bool:
        """
        This function DIRECTLY PUBLISHES the diagnostics for a file. 
        MUST BE CALLED AFTER register_new_diagnostic.
        """
        curr = self.conn.cursor()
        try:
            json_diagnostics_list = curr.execute("""
            SELECT diagnostics FROM all_diagnostics_view WHERE uri = ?
                              """, (document_uri,)).fetchall()

            if not len(json_diagnostics_list):
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.warning(f"No diagnostics for the file found . File : {document_uri}")
                return False
            
            pydantic_objekts_list = []
            for i in json_diagnostics_list:
                pydantic_objekts_list.append(
                        GeneralDiagnosticsPydanticObjekt.model_validate_json(i[0])
                        )
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt load diagnostics due to following error : {e}")
            return False
        finally:
            curr.close()

        document = self.ls.workspace.get_text_document(document_uri)

        diagnostics_lsprotocol_final_list = []

        try:
            diagnostics_lsprotocol_list = GeneralDiagnosticsPydanticToLSProtocol(self.ls, pydantic_objekts_list, document)
            for i in diagnostics_lsprotocol_list:
                diagnostics_lsprotocol_final_list.append(i)
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"couldnt convert diagnostics from pydantic to lsprotocol standarts due to the following error : {e}")
            return False

        try:
            with self.ls.diagnostics_lock:
                self.ls.diagnostics[document_uri] = (document.version, diagnostics_lsprotocol_final_list)
            self.ls.workspace_diagnostic_refresh(None)
        except Exception as e:
            if os.getenv("AI_DIAGNOS_LOG") is not None:
                logging.error(f"Couldnt publish diagnostics due to the following reason: {e}")
            self.ls.window_show_message(types.ShowMessageParams(types.MessageType(1), f"Couldnt publish diagnostics for the following reason : {e}"))
            return False

        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.info("Sucsessfully published diagnostics. ")
        return True
        
    
    def TTLBasedDeletionThread(self):
        curr = self.conn.cursor()
        while True:
            try:
                last_writes_list = curr.execute("""
                SELECT last_changed_at, uri FROM files
                                  """).fetchall()
                for i in last_writes_list:
                    if time.time() - i[0] > self.ttl_seconds_until_deletion:
                        if os.getenv("AI_DIAGNOS_LOG") is not None:
                            logging.info(f"file: {i[1]}, last_changed_at: {i[0]}")
                        with self.db_lock:
                            curr.execute("""
                            DELETE FROM files WHERE uri = ?
                                              """, (i[1],))
                        self.load_all_diagnostics()
                        if os.getenv("AI_DIAGNOS_LOG") is not None:
                            logging.info(f"Deleted all records for file {i[1]} because its last change time is {i[0]}")
                time.sleep(360)
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.info("Checked all the files")
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error(f"TTLBasedDeletionThread encoutered the following problem : {e}")

    def TTLBasedDiagnosticsInvalidationThread(self):
        """
    This thread checks for every diagnostic present its corresponding files last_change time, e.g. last
    write to it time, then
    matches it against the diagnostics creation time (via -), 
    and if the result is smaller then self.ttl_seconds_until_invalidation, 
    the diagnostic gets deleted from the DB. 
        """
        curr = self.conn.cursor()
        while True:
            try:
                all_diagnostics = curr.execute("""
                SELECT uri, created_at, diagnostics, diagnostics_type FROM all_diagnostics_view
                                              """).fetchall()

                for i in all_diagnostics:
                    file_change_time = curr.execute("""
                    SELECT last_changed_at FROM files WHERE uri = ?
                                             """, (i[0],)).fetchone()

                    if (file_change_time[0] - i[1]) > self.ttl_seconds_until_invalidation:
                    # This line means : 
                    # last_change_time - diagnostics creation time, wich results in 2 possibilities:
                    # case 1:
                    #     The result is negative, because diagnostics creation time is AFTER the last change time. 
                    # case 2:
                    #     The result is positive, because  diagnostics creation time is BEFORE the last change time. 
                    # 
                    # We want to delete diagnostics that were created before last write +self.ttl_seconds...
                        with self.db_lock:
                            curr.execute(f"""
                            DELETE FROM diagnostics_{i[3]} WHERE diagnostics = ?
                                              """, (i[2],))
                        self.load_diagnostics_for_file(i[0])
                        if os.getenv("AI_DIAGNOS_LOG") is not None:
                            logging.info(f"Deleted from {i[3]} diagnostics:{i[2]}, and called refesh on file: {i[0]}.")
                    else:
                        if os.getenv("AI_DIAGNOS_LOG") is not None:
                            logging.info(f"Did not delete, because last_changed_at = {file_change_time[0]}, and diagnostics were created at {i[1]}, with self.ttl_seconds_until_invalidation being {self.ttl_seconds_until_invalidation}")
                        
                time.sleep(2)
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error(f"TTLBasedDiagnosticsInvalidationThread encoutered the follwoign error: {e}")

def DiagnosticsHandlingSubsystemFactory(ls: AIDiagnosLSP,
                                        sqlite_db_name: str = "diagnostics.db",
                                        ttl_seconds_until_deletion: int = 2592000,
                                        ttl_seconds_until_invalidation: int = 15
                                        ) -> DiagnosticsHandlingSubsystemClass:
    return DiagnosticsHandlingSubsystemClass(ls=ls, 
                                             sqlite_db_name=sqlite_db_name,
                                             ttl_seconds_until_deletion=ttl_seconds_until_deletion,
                                             ttl_seconds_until_invalidation= ttl_seconds_until_invalidation
                                             )
