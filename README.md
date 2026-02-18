# ai_diagnos.nvim

A Neovim plugin that adds AI‑powered diagnostics to your editor. It runs a Python‑based language server that uses LangChain to query various LLM providers (Gemini, OpenRouter, Groq) or an “Omniprovider” that falls back through them. Diagnostics are displayed just like native LSP diagnostics.

## Features

- **Pull‑based diagnostics** – triggered on file open, save, or manually.
- **Multiple AI providers** – Gemini, OpenRouter, Groq, or an Omniprovider that chains them.
- **Configurable debouncing** – prevents spam during rapid edits.
- **Fully configurable analysis** - You decide what analysers run and when
- **Custom diagnostic symbols** – mark AI‑generated diagnostics with a custom symbol (e.g. `AI`).
- **Commands** – analyse, clear, or clear all diagnostics.
- **Graceful fallback** – Omniprovider automatically tries the next provider on failure (rate limits, downtime).
- **Semantic location matching** – uses exact code snippets, not line numbers, wich reduces halucinated errors greatly. 
- **Diagnostics storage and reusal** - uses SQLite to store the diagnostics for reusal (Fully configurable pruning included)
- **Cross File analysis** - Import resolution and cross file content gathering 


> [!NOTE]
> cross file analysis only has built in parser for python. 
> I cant write more of them, that is too complex
> I will write a plugin system with a clear API that lets you write your own in whatever language you want and just plug in for the language its for. 
> (If anyone is capable of writing a parser for all the languages, even a small tipp on how to do that better is appreciated)


## Requirements

- Neovim ≥ 0.9.0 (with `vim.lsp`, `vim.diagnostic`)
- Python ≥ 3.9
- `pip` and `venv`
- optionaly uv
- An API key for at least one of the supported providers

## Installation

### With [lazy.nvim](https://github.com/folke/lazy.nvim)

```lua
{
    "VectorZeroAI/ai_diagnos.nvim",
    build = function()
        require("ai_diagnos").build()   -- sets up Python virtualenv and installs dependencies
    end,
    dependencies = {
        "nvim-lua/plenary.nvim",
        "neovim/nvim-lspconfig",
    },
    config = function()
        require("ai-diagnostics").setup({
            -- your configuration (see below)
        })
    end,
}
```

> [!NOTE]
> The lsp itself in its own repo, wich is at https://github.com/VectorZeroAI/ai-diagnos-lsp
> Its fetched as submodule to the neovim plugin

> **⚠️ Note on the build system**  
> Its pretty bad. 
> If it doesnt work, referense the manual installation section

#### build system parameters

| param | default_value | explanation |
| ------------- | ---------- | ------------ |
| use_uv  | false | tells the build system if it should use uv or not. (Not means pip) |
| install_to_venv | true | tells the build system if its supposed to use a virtual env to not install the lsps deps globaly to your system |


### Manual installation

- You can clone ether the plugin repo, or the dedicated lsp repo. plugin repo is where your reading this from, and lsp is at : https://github.com/VectorZeroAI/ai-diagnos-lsp
- Then you go into that repo, and you install the python project
    - The command for that is the following:
    - with uv:
        - uv sync
        - uv pip install .
    - with pip:
        - pip install .

> [!NOTE]
> uv is just faster. pip is available everywhere. 


## Configuration

Call `require("ai-diagnostics").setup({...})` in your Neovim config. All parameters are optional except the API key(s) for the provider(s) you enable.

| Parameter                     | Type               | Default                                   | Description |
|-------------------------------|--------------------|-------------------------------------------|-------------|
| `api_key_openrouter`          | `string`           | –                                         | **Required** for OpenRouter or Omniprovider. |
| `api_key_gemini`             | `string`           | –                                         | **Required** for Gemini or Omniprovider. |
| `api_key_groq`              | `string`           | –                                         | **Required** for Groq or Omniprovider. |
| `use_gemini`                 | `boolean`          | `false`                                   | Enable only Gemini. |
| `use_openrouter`             | `boolean`          | `false`                                   | Enable only OpenRouter. |
| `use_groq`                   | `boolean`          | `false`                                   | Enable only Groq. |
| `use_omniprovider`           | `boolean`          | `true`                                    | Try OpenRouter → Gemini → Groq. |
| `model_openrouter`           | `string`           | `"tngtech/tng-r1t-chimera:free"`          | Model name for OpenRouter. |
| `model_gemini`              | `string`           | `"gemini-2.5-flash-lite"`                | Model name for Gemini. |
| `model_groq`                | `string`           | `"openai/gpt-oss-120b"`                  | Model name for Groq. |
| `fallback_models_gemini`    | `table` (strings)  | `{"gemini-2.5-flash", "gemini-3-flash-preview"}` | Fallback models for Gemini. |
| `fallback_models_groq`      | `table` (strings)  | `{"openai/gpt-oss-20b", "openai/gpt-oss-safeguard-20b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"}` | Fallback models for Groq. |
| `debounce_ms`               | `integer`          | `3000`                                   | Minimum time (ms) between diagnostics for the same file. |
| `max_file_size`             | `integer`          | `10000`                                  | Maximum number of lines to analyse. Larger files are skipped. |
| `timeout`                   | `integer`          | `99999`                                  | Maximum wait time (seconds) for the LLM to respond. |
| `show_progress`             | `boolean`          | `true`                                   | Show periodic progress notifications via `vim.notify()`. |
| `show_progress_every_ms`    | `integer`          | `5000`                                   | Interval between progress notifications. |
| `ai_diagnostics_symbol`     | `string`           | `"AI"`                                   | Sign text for AI diagnostics. |
| `cmd`                       | `table` (strings)  | `{"ai-diagnos-lsp"}`                     | Command to start the LSP. |
| `filetypes`                 | `table` (strings)  | `{"python", "go", "lua"}`                | Filetypes to attach the LSP to. |
| `root_dir`                  | `function`         | `lspconfig.util.root_pattern(".git")`    | Root directory detection. |
| `on_attach`                 | `function`         | `nil`                                    | Callback when the LSP attaches. |
| `capabilities`              | `table`            | `nil`                                    | LSP client capabilities. |
| `AnalysisSubsystem`         | `table`            | explained in its corresponding section   | explained in its corresponding section   |
| `CrossFileAnalysis`         | `table`            | explained in its corresponding section   | explained in its corresponding section   |
| `DiagnosticsSubsystem`         | `table`            | explained in its corresponding section   | explained in its corresponding section   |

> ⚠️ **Important**  
> Only **one** of `use_gemini`, `use_openrouter`, `use_groq`, or `use_omniprovider` should be `true` at a time. The plugin does **not** enforce this; enabling more than one leads to undefined behaviour.
> also, just a quick note, I am thinking of removing this functionality, and basically making everything omniprovider, since omniprovider can have the added functionality of skipping providers where api_key = ""
> but I would like to hear if I should remove it or not. 

### AnalysisSubsystem
| value | type | default | explanation |
| --------------- | --------------- | --------------- | --------------- | 
| write | list of analysis types.  | [ "CrossFile", "Basic" ] | Tells the analysis subsystem what analyses to run on write to a file. The list of all the supported analysis types can be seen in its corresponding section |
| open | list of analysis types.  | [ "CrossFile", "Basic" ] | Tells the analysis subsystem what analyses to run on open to a file. The list of all the supported analysis types can be seen in its corresponding section |
| change | list of analysis types.  | [ ] | Tells the analysis subsystem what analyses to run on change to a file. The list of all the supported analysis types can be seen in its corresponding section |
| command | list of analysis types.  | [ "CrossFile", "Basic" ] | Tells the analysis subsystem what analyses to run on command to a file. The list of all the supported analysis types can be seen in its corresponding section |
| max_threads | integer | 5 | Tells the analysis subsystem how many analyses can be run at once. Does not correspond to actual thread amount, but kinda limits it. (Threads spawn threads, so the actual amount is basically times 3 that defined here. Any suggestions on how to fix that are wellcome) |
> [!NOTE]
> I plan to make the command take the analysis type in as an argument, but that is for the future. 
> [!NOTE]
> The analyses on open run only if no cached analyses were found. More on cache and reusal in the Diagnostics Subsystem section

### CrossFileAnalysis

| value | type | default | explanation |
| ----- | ---- | ---- | ------ |
| scope | list of strings | No applicable default provided | is a list of scopes that limit what the cross file analysis takes in. (IDK if it actually works. )
| max_analysis_depth | None or int | None | limits how many times the cross file analysis recursivly checks for imports. None means check until everything is cleared.  |
| max_string_size_char | int or None | 1000000 | limits how many characters long a context may be at maximum. Everything beyond that is simply excluded from the context |

### DiagnosticsSubsystem

| value | type | default | explanation |
| ----- | ---- | ---- | ------ |
| check_ttl_for_deletion | int or float | 360 | Every how many seconds the background thread that checks for file deletions should be checking for files viability to deletion |
| sqlite_db_name | string | "diagnostics.db" | The sqlite database file name. Why would you ever want to change that ?  |
| check_ttl_for_invalidation | int or float | 5 |  Every how many seconds a background thread for stale / invalid diagnostics and delete them  |
| ttl_until_deletion | int or float | 2592000 | After how much time of not being written to should a files diagnostics be fully errased from the database; defaults to 30 days.  |
| ttl_until_invalidation |  int or float | 15 | How many seconds after a new write to the file should the old diagnostics be errased.  |

> [!IMPORTANT]
> If you specify a subsystems configuration in your config, you must specify all the values. Because I couldnt get recursive table merging to work. Any suggestions on that are wellcome. 

## Usage

Once configured, the LSP client is automatically started for matching filetypes. Diagnostics are requested:

- When a file is **opened**
- When a file is **saved**
- When a file is **changed** (optionaly)
- Manually via the `:AIAnalyse` command

### User Commands

| Command              | Description |
|----------------------|-------------|
| `:AIAnalyse`        | Force a new AI diagnostic analysis for the current buffer. |
| `:AIClear`          | Clear AI diagnostics for the current buffer. |
| `:AIClearAll`       | Clear **all** AI diagnostics across all buffers. |
| `:AIStatus`         | Show current status of the AI LSP. |

## Supported Providers

### Gemini
- Uses `langchain-google-genai`.
- Configure with `use_gemini = true`, `api_key_gemini`, and optionally `model_gemini` / `fallback_models_gemini`.

### OpenRouter
- Uses `langchain-openai` (OpenAI‑compatible endpoint).
- Configure with `use_openrouter = true`, `api_key_openrouter`, and optionally `model_openrouter`.
- No model fallbacks, because they make no sense for openrouter, with how it counts usage.

### Groq
- Uses `langchain-groq`.
- Configure with `use_groq = true`, `api_key_groq`, and optionally `model_groq` / `fallback_models_groq`.
> [!NOTE]
> use_groq is not yet implemented. Just use omniprovider and make all the other api keys blank

### Omniprovider
- Tries **OpenRouter** first, then **Gemini**, then **Groq**.
- Requires all three API keys. (doesnt require them to be valid nor not "")
- Configure with `use_omniprovider = true` (this is the default).
- Each provider may still use its own model‑level fallbacks.

## How It Works

The plugin is split into two parts:

1. **Neovim Lua client** (`ai_diagnos.lua`)  
   - Registers the LSP server via `lspconfig`.  
   - Forwards user configuration as `init_options`.  
   - Sets up auto‑commands and user commands.  
   - provides a building function.

1. **Python LSP server** (`main.py`)  
   - Built with [`pygls`](https://pygls.readthedocs.io/).  
   - Receives `initialize` with configuration.  
   - On `didOpen` / `didSave` /  `didChange` custom command, starts a **worker thread** that:  
     - Verifies file size and debounce.  
     - Builds the appropriate LangChain (Gemini, OpenRouter, Groq, or Omniprovider).  
     - Invokes the chain with the file content.  
     - Parses the JSON response (using Pydantic).  
     - Uses `grep()` to locate each diagnostic by **exact source snippet** (the AI is instructed to copy the exact code fragment).  
     - stores the result into the Diagnostics Handling Subsystem
         - Diagnostics handling subsystem stores the result with timestamp into the corresponding table. 
     - Tells the Diagnostics Handling subsystem to load the diagnostics for that file into the memory. 
         - Diagnostics Handling subsystem makes them available for the main lsp to grab
         - as well as notifies the client of the new diagnostics available
         - Client pulls them

- If the AI hallucinates a location that cannot be found, the diagnostic is silently skipped.
- All API calls are **non‑blocking**; Neovim remains responsive. (They also dont block each-other)

****

## Troubleshooting

### The LSP server does not start

- Check that the Python virtual environment exists and is installed:  
  `~/.local/share/nvim/lazy/ai_diagnos.nvim/python3/venv/bin/python -m ai_diagnos_lsp`
- Ensure you have all required API keys in your environment or config.
- Set the environment variable `AI_DIAGNOS_LOG=1` to enable detailed logging to `ai_diagnos_lsp.log` in Neovim’s working directory.

### Build fails / “command not found”

- Follow the **manual installation** steps under [Installation](#installation).

### Diagnostics never appear

- Check the log file for errors (see above).
- Verify that the file type is in `filetypes` (default: `python`, `go`, `lua`).
- Ensure the file size is below `max_file_size`.
- If using Omniprovider, confirm all three API keys are set – otherwise the chain will fail.

****

## Roadmap / TODO

- [ ] Write a logic analyser (With both CrossFile and Basic versions)
- [ ] Write a style analyser (With both CrossFile and Basic versions)
- [ ] Write a parser plugin system.
- [ ] prepare and release

****

## Plan:

- [ ] Add support for Claude API
- [ ] Add support for OpenAI API
- [ ] Add support for Github AI thingy I saw (if possible)


> [!NOTE]
> Requests to add provider support are also valuable feedback. 
> I will add that as soon as I can. 

****

## Contributing

Contributions of any kind are welcome!  
Open an issue or a pull request or smt. 

## Feedback

Feedback is appreciated and wellcome. 
You may open an issue and put your ideas or suggestions there.
Any constructive feedback will be helpfull to the project, even if its just a feature idea
