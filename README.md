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
            use_omniprovider = true,
            api_key_openrouter = vim.env.OPENROUTER_API_KEY,
            model_openrouter = "anthropic/claude-3.5-sonnet",
            debounce_ms = 2000,
            max_file_size = 10000,
            api_key_gemini = vim.env.GEMINI_API_KEY,
            api_key_groq = vim.env.GROQ_API_KEY,
        })
    end
}

~~~

> [!NOTE]
> Build system only works on linux now, if it actually works, also it sucks. The LSP is in the same repo as this lua plugin, so you can just go to where neovim cloned that, and run pip install . inside the python3 directory to get that working. 

TODO: FIX THE BUILD SYSTEM 

## Supported API providers :
1. Gemini. To activate put use_gemini = true, use_omniprovider = false in the config. 
2. Openrouter. To activate put use_openrouter = true, use_omniprovider = false in the config. 
3. Groq. TODO : ADD the support for it only. 
4. Omniprovider. To activate put use_omniprovider = true in the config. 
5. 
> [!NOTE]
> Only one of the use parameters is allowed at a time, but the programm doesnt yet check that, so its your responsibility to not hit undefined behaviour by putting 2 use parameters to true

Omniprovider basically chains every provider one after anouther, on fail of the previous, for example due to rate limiting. 
Technically you can just use omniprovider with garbage as api_keys for all the providers exept the one you want and it will still work. 

## Parameters:

| parameter | role | example value | optional ? |
| api_key_openrouter | I is an required parameter, used to acsess the API. | "sadgubwqeogfUWHEGHBAWELIGUBAIRUGBeirgbea" | requred for openrouter or omniprovider. Not if not using that. |
| model_openrouter |  optional parameter, tells the plugin wich OpenRouter model to use, defaults to antropic/claude-3.5-sonnet. | "anthropic/claude-3.5-sonnet" | optional |
| debounce_ms |  optional parameter, defines how muchtime is the minimum between 2 writes is required to activate a new API call, to prevent the write spam from causing problmes. | 3000 | optional |
| max_file_size |  optional parameter, defines the maimal file size (in lines) in order to prevent the model from analysing files that are to big. | 12000 | optional |
| show_progress |  Boolean, optional parameter. It uses vim.notify("notification") to inform the users of the progress, so the users dont try to save the file again, since API calls create invisible wait perioudes. | true | optional |
| root_dir |  optional parameter, tells the LSP how to find the root dir. Default value is ".git". | TODO: ADD | optinal |
| cmd |  optional parameter, lets you change the command for initialising the connection with LSP. May or may not be usefull .  | TODO: ADD | optinal |
| show_progress_every_ms |  optional, Tells the interval of how often the LSP should ping them with "Im still running" | TODO: ADD | optional |
| ai_diagnostics_symbol |  optional, Tells the client how to display AI diagnostics. Default value is "AI" NOTE THAT IT DOESNT WORK RIGHT NOW. | "AI" | optional | 
| model_gemini | optional parameter. Tells the LSP wich gemini model to use | gemini-2.5-flash | optional |
| model_groq | optional parameter. Tells the LSP wich groq model to use | openai/gpt-oss-20b | optional |
| fallback_models_gemini | Optional parameter. Tells wich models to fallback to if the main model fails. | gemini-2.5-flash-lite | optional |
| fallback_models_groq | Optional parameter. Tells wich models to fallback to if the main model fails. | openai/gpt-oss-120b | optional |
| use_gemini | tells the system to use gemini. The same way as defined above. | required |
| use_openrouter | tells the system to use openrouter. | required |
| use_omniprovider | tells the system to use omniprovider | requred |
| api_key_gemini | The api key for gemini | "aofnsrbgosurgbiaebrgi" | required for gemini usage |
| api_key_groq | the api key for groq usage | "gwoarugpaenmcaocr" | required for groq usage | 

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

## ai_diagnos_lsp/main.py

Composes and exposes the analysers functions, and cleanly exposes them for the lua part. 
It does so in the same way an actual LSP would do it. 
That also lets the projekt be expanded into a fullblown LSP. 
So, it uses pygls and composes the LSP. 

The analyser is the analyser.py file that gets functions imported from and just used. 

### analysers/

For now it only has one analysis method, wich is the basic analysis method. 
I will add other methods in the future, as well as make wich one touse as the base a configurable choise. 

#### chains/

Here I put the Langchain chains I have

Each one of them is basically the same thing, but has a different prompt, and these are activated in different times. 
> [!NOTE]
> The lua part exposes editor commands that activate each one of those. 


# Contributing 

Any contribution in any form is welcomed. 
It may take a while for me to actually merge a PR, but I am still the maintainer and am still working on this. Not actively though, as I am genuenly bad at lua. 

