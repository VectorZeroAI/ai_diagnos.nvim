# ai_diagnos.nvim
Neovim plugin that adds AI diagnostics to neovim. 

# Usage

To activate the plugin, use the following:

with lazy.nivm:
~~~lua

{
    "VectorZeroAI/ai_diagnos.nvim",
    build = function ()
        require('ai_diagnos_lsp').build()
    end
    dependencies = { "nvim-lua/plenary.nvim", "neovim/nvim-lspconfig" },
    config = function()
        require("ai-diagnostics").setup({
            api_key = vim.env.OPENROUTER_API_KEY,
            model = "anthropic/claude-3.5-sonnet",
            debounce_ms = 2000,
            max_file_size = 10000
        })
    end
}

~~~

## Parameters:

| parameter | role | example value |
| ------------- | -------------- | -------------- |
| api_key | I is an required parameter, used to acsess the API. | "sadgubwqeogfUWHEGHBAWELIGUBAIRUGBeirgbea" |
| --------------- | ---------- | ------------ |
| model |  optional parameter, tells the plugin wich OpenRouter model to use, defaults to antropic/claude-3.5-sonnet. | "anthropic/claude-3.5-sonnet"
| --------------- | ---------- | ------------ |
| debounce_ms |  optional parameter, defines how muchtime is the minimum between 2 writes is required to activate a new API call, to prevent the write spam from causing problmes. | 3000
| --------------- | ---------- | ------------ |
| max_file_size |  optional parameter, defines the maimal file size (in lines) in order to prevent the model from analysing files that are to big. | TODO: ADD |
| --------------- | ---------- | ------------ |
| show_progress |  Boolean, optional parameter. It uses vim.notify("notification") to inform the users of the progress, so the users dont try to save the file again, since API calls create invisible wait perioudes. | TODO: ADD |
| --------------- | ---------- | ------------ |
| root_dir |  optional parameter, tells the LSP how to find the root dir. Default value is ".git". | TODO: ADD |
| --------------- | ---------- | ------------ |
| cmd |  optional parameter, lets you change the command for initialising the connection with LSP. May or may not be usefull .  | TODO: ADD |
| --------------- | ---------- | ------------ |
| show_progress_every_ms |  optional, Tells the interval of how often the LSP should ping them with "Im still running" | TODO: ADD |
| --------------- | ---------- | ------------ |
| ai_diagnostics_symbol |  optional, Tells the client how to display AI diagnostics. Default value is "AI" | TODO: ADD |
| --------------- | ---------- | ------------ |

## Commands:
1. AIClear --> clears all the AI diagnostics
2. AIAnalyse --> forces rediagnosing the file.
3. AIStatus --> Outputs status   
> [!NOTE]
> Doesnt work right now. I am still implementing that.

# Architecture
(The new)
ai_diagnos.lua is the file responsible for calling python LSP .
AI_LSP.py is the python based AI LSP, wich does the actual AI stuff. 

AI_LSP.py will use Langhchain with Openrouter API for the actual analysis and diagnostics. 
ai_diagnos.lua is the lua file responsible for providing tasks and context to the AI_LSP 

## ai_diagnos.lua architecture
I dont know yet myself. 
> [!NOTE]
> Each one of the analysers methods are exposed as Editor Commands and can be called manually or via autocmd. Autocmd is also the recommended way to do that and to configure the plugin. It exposes an option to do so automatically. 

## AI_LSP.py 

Composes and exposes the analysers functions, and cleanly exposes them for the lua part. 
It does so in the same way an actual LSP would do it. 
That also lets the projekt be expanded into a fullblown LSP. 
So, it uses pygls and composes the LSP. 

The analyser is the analyser.py file that gets functions imported from and just used. 

### analyser.py

analyser exposes the following analysis methods: 

general_analysis

logic_analysis

optimisation_suggestions

Each one of them is basically the same thing, but has a different prompt, and these are activated in different times. 
> [!NOTE]
> The lua part exposes editor commands that activate each one of those. 


# Contributing 

Any contribution in any form is welcomed. 
It may take a while for me to actually merge a PR, but I am still the maintainer and am still working on this. Not actively though, as I am genuenly bad at lua. 

