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
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```


## SQL Schema
