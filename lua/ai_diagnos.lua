local M = {}

-- Default configuration
local default_config = {
    cmd = { "python3", "-m", "ai_diagnos_lsp" }, -- Adjust this to match your LSP server command
    filetypes = { "*" }, -- All filetypes by default
    root_dir = nil, -- Will use vim's cwd by default
    settings = {},
}

-- Store the user configuration
M.config = vim.deepcopy(default_config)

-- Setup function called by users in their config
function M.setup(user_config)
    user_config = user_config or {}
    M.config = vim.tbl_deep_extend("force", default_config, user_config)
    
    -- Register the LSP server configuration
    local lspconfig = require("lspconfig")
    local configs = require("lspconfig.configs")
    
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

