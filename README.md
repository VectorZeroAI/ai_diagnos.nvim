# ai_diagnos.nvim
Neovim plugin that adds AI diagnostics to neovim. 

# ai_diagnos.nvim
Neovim plugin that adds AI diagnostics to neovim.

# Usage

To activate the plugin, use the following:

with lazy.nivm:
~~~lua

{
    "VectorZeroAI/ai_diagnos.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
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

1. api_key --> is an required parameter, used to acsess the API.
2. model --> optional parameter, tells the plugin wich OpenRouter model to use, defaults to antropic/claude-3.5-sonnet.
3. debounce_ms --> optional parameter, defines how muchtime is the minimum between 2 writes is required to activate a new API call, to prevent the write spam from causing problmes.
4. max_file_size --> optional parameter, defines the maimal file size (in lines) in order to prevent the model from analysing files that are to big.
5. show_progress --> Boolean, optional parameter. It uses vim.notify("notification") to inform the users of the progress, so the users dont try to save the file again, since API calls create invisible wait perioudes.

## Commands:
1. AIToggle --> toggles the AI diagnositics on and off
2. AIClear --> clears all the AI diagnostics
3. AIAnalyse --> forces rediagnosing the file.
4. AIStatus --> Outputs status
