local M = {}

-- Default configuration
local script_path = debug.getinfo(1, "S").source:sub(2)
local plugin_dir = vim.fn.fnamemodify(script_path, ':h')
local python_script = plugin_dir .. '/../python3/ai_diagnos_lsp.py'

local configs = require('lspconfig.configs')

configs.ai_diagnos_lsp = {
    default_config = {
        cmd = { 'python3', python_script },
        filetypes = { 'python', 'go' }, 
        root_dir = require('lspconfig').util.root_pattern('.git'),
    },
}

-- Store the user configuration
M.config = vim.deepcopy(configs.ai_diagnos_lsp.default_config)

-- Setup function called by users in their config
function M.setup(user_config)
    M.config = vim.tbl_deep_extend("force", configs.ai_diagnos_lsp.default_config, M.config)
    
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

