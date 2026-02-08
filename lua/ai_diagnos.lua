local M = {}

-- Setup function called by users in their config
function M.setup(user_config)

    local configs = require('lspconfig.configs')

    if user_config.api_key == nil then
        print("API key is required for the system to function normally")
        error("API key parameter is required. please include it in your config", 2)
    end

    local default_config = {
        cmd = { 'ai-diagnos-lsp' },
        filetypes = { 'python', 'go', 'lua' },
        root_dir = require('lspconfig').util.root_pattern('.git'),
        settings = {},
        on_attach = nil,
        capabilities = nil,
        init_options = {},
    }
    M.config = {
            cmd = user_config.cmd or default_config.cmd,
            filetypes = user_config.filetypes or default_config.filetypes,
            root_dir = user_config.root_dir or default_config.root_dir,
            settings = user_config.settings or default_config.settings,
            on_attach = user_config.on_attach or default_config.on_attach,
            capabilities = user_config.capabilities or default_config.capabilities,
            init_options = user_config.api_key or default_config.init_options,
        }
    -- Register the LSP server configuration
    local lspconfig = require("lspconfig")
    -- Define the server if not already defined
    if not configs.ai_diagnos then
        configs.ai_diagnos = {
            default_config = {
                cmd = M.config.cmd,
                filetypes = M.config.filetypes,
                root_dir = M.config.root_dir,
                settings = M.config.settings,
                name = "ai_diagnos_lsp",
            },
        }
    end
    -- Setup the LSP client
    lspconfig.ai_diagnos.setup({
        cmd = M.config.cmd,
        filetypes = M.config.filetypes,
        root_dir = M.config.root_dir,
        settings = M.config.settings,
        on_attach = M.config.on_attach,
        capabilities = M.config.capabilities,
        init_options = M.config.init_options,
    })
end

return M
