# ai_diagnos.nvim

A Neovim plugin that adds AI‑powered diagnostics to your editor. It runs a lightweight Python‑based language server that uses LangChain to query various LLM providers (Gemini, OpenRouter, Groq) or an “Omniprovider” that falls back through them. Diagnostics are displayed just like native LSP diagnostics.

## Features

- **Pull‑based diagnostics** – triggered on file open, save, or manually.
- **Multiple AI providers** – Gemini, OpenRouter, Groq, or an Omniprovider that chains them.
- **Configurable debouncing** – prevents spam during rapid edits.
- **Custom diagnostic symbols** – mark AI‑generated diagnostics with a custom sign (e.g. `AI`).
- **Commands** – analyse, clear, or clear all diagnostics.
- **Graceful fallback** – Omniprovider automatically tries the next provider on failure (rate limits, downtime).
- **Semantic location matching** – uses exact code snippets, not line numbers, so hallucinations are simply ignored.

## Requirements

- Neovim ≥ 0.9.0 (with `vim.lsp`, `vim.diagnostic`)
- Python ≥ 3.9
- `pip` and `venv`
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

> **⚠️ Note on the build system**  
> The built‑in `build()` currently only works reliably on Linux. If it fails, please install the Python server manually:
> ```bash
> cd ~/.local/share/nvim/lazy/ai_diagnos.nvim/python3
> python -m venv venv
> .venv/bin/python -m pip install -e .
> ```
> After that, the plugin will automatically use this virtual environment.

### With packer.nvim

```lua
use {
    "VectorZeroAI/ai_diagnos.nvim",
    run = function()
        require("ai_diagnos").build()
    end,
    requires = { "nvim-lua/plenary.nvim", "neovim/nvim-lspconfig" },
    config = function()
        require("ai-diagnostics").setup({ ... })
    end,
}
```

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

> ⚠️ **Important**  
> Only **one** of `use_gemini`, `use_openrouter`, `use_groq`, or `use_omniprovider` should be `true` at a time. The plugin does **not** enforce this; enabling more than one leads to undefined behaviour.

## Usage

Once configured, the LSP client is automatically started for matching filetypes. Diagnostics are requested:

- When a file is **opened**
- When a file is **saved**
- Manually via the `:AIAnalyse` command

### User Commands

| Command              | Description |
|----------------------|-------------|
| `:AIAnalyse`        | Force a new AI diagnostic analysis for the current buffer. |
| `:AIClear`          | Clear AI diagnostics for the current buffer. |
| `:AIClearAll`       | Clear **all** AI diagnostics across all buffers. |
| `:AIStatus`         | (⚠️ not yet implemented) Show current status of the AI LSP. |

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

### Omniprovider
- Tries **OpenRouter** first, then **Gemini**, then **Groq**.
- Requires all three API keys.
- Configure with `use_omniprovider = true` (this is the default).
- Each provider may still use its own model‑level fallbacks.

## How It Works

The plugin is split into two parts:

1. **Neovim Lua client** (`ai_diagnos.lua`)  
   - Registers the LSP server via `lspconfig`.  
   - Forwards user configuration as `init_options`.  
   - Sets up auto‑commands and user commands.  
   - Provides a fallback build routine.

1. **Python LSP server** (`main.py`)  
   - Built with [`pygls`](https://pygls.readthedocs.io/).  
   - Receives `initialize` with configuration.  
   - On `didOpen` / `didSave` / custom command, starts a **worker thread** that:  
     - Verifies file size and debounce.  
     - Builds the appropriate LangChain (Gemini, OpenRouter, Groq, or Omniprovider).  
     - Invokes the chain with the file content.  
     - Parses the JSON response (using Pydantic).  
     - Uses `grep()` to locate each diagnostic by **exact source snippet** (the AI is instructed to copy the exact code fragment).  
     - Converts the result to LSP `Diagnostic` objects.  
     - Publishes diagnostics via `textDocument/publishDiagnostics` (pull diagnostics are also supported).

- If the AI hallucinates a location that cannot be found, the diagnostic is silently skipped.
- All API calls are **non‑blocking**; Neovim remains responsive.

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

## Roadmap / TODO

- [ ] Add a diagnostics storage and retrieval system for repeted or multiple diagnostics on the same file. 
- [ ] Expose more analysers and analysis types (e.g. logic error specific, performance specific, style specific, etc. )
- [ ] Implement the AI status command

## Contributing

Contributions of any kind are welcome!  
Open an issue or a pull request.  
But do not expect much, I am still a beginner.

