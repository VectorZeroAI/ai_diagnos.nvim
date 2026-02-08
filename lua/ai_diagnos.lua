local M = {}

-- Setup function called by users in their config
function M.setup(user_config)

    local configs = require('lspconfig.configs')

    if user_config.api_key == nil then
        print("API key is required for the system to function normally")
        error("API key parameter is required. please include it in your config", 2)
    end

    local default_config = {
        cmd = { 'ai-diagnos-lsp', user_config.api_key },
        filetypes = { 'python', 'go', 'lua' },
        root_dir = require('lspconfig').util.root_pattern('.git'),
    }
    M.config = vim.tbl_deep_extend("force", default_config, user_config)
    -- Register the LSP server configuration
    local lspconfig = require("lspconfig")
    -- Define the server if not already defined
    if not configs.ai_diagnos then
        configs.ai_diagnos = {
            default_config = {
                cmd = M.config.cmd,
                filetypes = M.config.filetypes,
                root_dir = M.config.root_dir or function()
                    return vim.fn.getcwd()
                end,
                settings = M.config.settings,
                name = "ai_diagnos",
            },
        }
    end
    -- Setup the LSP client
    lspconfig.ai_diagnos.setup({
        cmd = M.config.cmd,
        filetypes = M.config.filetypes,
        root_dir = M.config.root_dir or function()
            return vim.fn.getcwd()
        end,
        settings = M.config.settings,
        on_attach = M.config.on_attach,
        capabilities = M.config.capabilities,
    })
end

return M

