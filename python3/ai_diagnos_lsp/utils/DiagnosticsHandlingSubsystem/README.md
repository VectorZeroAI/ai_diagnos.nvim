# Diagnosics Handling subsystem

This is the file where I put the diagnostics handling documentation. 

The diagnostics handling subsystem is a class that is created in the ls class under DiagnosticsHandlingSubsystem . 

The subsystem is currently located under utils/DiagnosticsHandlingSubsystem

# Architecture
I will explain the architecture the best I can.
> [!NOTE]
> The server is pull based, so **publishing** refers to exposing them to the client

## On creation : 
On construction of the class, it builds an SQLite DB for diagnostics storage. 

## Exposes methods:
| method | parameters | explanation | usage_example |
| ------------- | -------------- | -------------- | ------------- |
| load_all_diagnostics | None | Loads and publishes all the diagnostics from the DB. Also tells the client to update the diagnostics | load_all_diagnostics(None) |
| load_diagnostics_for_file | uri | Loads the diagnostics for a single file. Also tells the client to refresh diagnostics | load_diagnostics_for_file(doc.uri) |
| save_new_diagnostics() | DiagnosticsPydanticObjekt ; Diagnostics Type | This method saves new diagnostics to the DB.  | save_new_diagnostics(New_Diagnostics_fresh_from_Langchain, "Deep") |
| register_new_write(uri) | uri | registeres a new write to the DB. | register_new_write(params.document.uri) |


## Operational Schema
```mermaid
flowchart TB
    subgraph AIDiagnosLSP["AIDiagnosLSP (Main Server)"]
        direction LR
        LS[("LSP Server Instance")]
    end

    subgraph DHS["DiagnosticsHandlingSubsystem"]
        direction TB
        DHS_obj["DiagnosticsHandlingSubsystemClass"]
        DB_lock["threading.Lock()"]
        conn[("SQLite Connection<br/>(diagnostics.db)")]
        ttl_del["TTLBasedDeletionThread<br/>(runs every 360s)"]
        ttl_inv["TTLBasedDiagnosticsInvalidationThread<br/>(runs every 2s)"]

        DHS_obj --> DB_lock
        DHS_obj --> conn
        DHS_obj --> ttl_del
        DHS_obj --> ttl_inv

        subgraph methods["Callable Methods"]
            register_file_write()["register_file_write"]
            save_new_diagnostic()["save_new_diagnostic"]
            load_all_diagnostics()["load_all_diagnostics"]
            load_diagnostics_for_file()["load_diagnostics_for_file"]
        DHS_obj ---> methods
    end

    subgraph Database["SQLite Schema"]
        direction LR
        files["files<br/>(uri, last_changed_at)"]
        diag_basic["diagnostics_Basic<br/>(uri, diagnostics, created_at)"]
        diag_cross["diagnostics_CrossFile<br/>(...)"]
        diag_logic["diagnostics_Logic<br/>(...)"]
        diag_style["diagnostics_Style<br/>(...)"]
        diag_security["diagnostics_Security<br/>(...)"]
        diag_deep["diagnostics_Deep<br/>(...)"]
        view["all_diagnostics_view<br/>(UNION of all diagnostic tables)"]

        files --> view
        diag_basic --> view
        diag_cross --> view
        diag_logic --> view
        diag_style --> view
        diag_security --> view
        diag_deep --> view
    end

    subgraph Conversion["Diagnostic Conversion"]
        func["GeneralDiagnosticsPydanticToLSProtocol()"]
        grep["grep() utility<br/>(text search)"]
        severity["severity_map"]
        func --> grep
        func --> severity
    end

    subgraph External["External World"]
        Client[("LSP Client")]
        FileSystem[("File System")]
        AIAnalysis[("AI Analysis Module")]
    end

    %% Interactions
    AIAnalysis -- "calls save_new_diagnostic()" --> DHS
    FileSystem -- "file save triggers<br/>register_file_write()" --> DHS

    DHS -- "reads/writes" --> Database
    DHS -- "uses" --> Conversion

    DHS -- "publishes diagnostics via<br/>workspace/diagnostic/refresh" --> Client

    ttl_del -- "deletes old file records<br/>based on last_changed_at" --> Database
    ttl_inv -- "deletes stale diagnostics<br/>(last_change - created_at > ttl_invalidation)" --> Database

    load_diagnostics["load_all_diagnostics() / load_diagnostics_for_file()"] --> Conversion
    Conversion -- "produces types.Diagnostic[]" --> LS
    LS --> Client
```


## SQL Schema
