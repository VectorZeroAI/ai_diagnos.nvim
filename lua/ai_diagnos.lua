local M = {}

---@class AIDiagnosLSPConfig
---
---@field cmd string[]
---@field filetypes string[]
---@field root_dir function
---@field on_attach function | nil
---@field capabilities lsp.ClientCapabilities | nil
---
---@field timeout number
---@field debounce_ms number
---@field max_file_size number
---@field show_progress boolean
---@field show_progress_every_ms number
---@field ai_diagnostics_symbol string
---
---@field use_omniprovider boolean
---
---@field use_gemini boolean
---@field model_gemini string
---@field fallback_models_gemini string[]
---
---@field use_openrouter boolean
---@field model_openrouter string
---
---@field use_groq boolean
---@field model_groq string
---@field fallback_models_groq string[]
---
---@field AnalysisSubsystem table<"write" | "open" | "change" | "command" | "max_threads", string[] | number>

---@type AIDiagnosLSPConfig
local default_config = {
    cmd = { 'ai-diagnos-lsp' },
    filetypes = { 'python', 'go', 'lua' },
    root_dir = require('lspconfig').util.root_pattern('.git'),
    on_attach = nil,
    capabilities = nil,

    timeout = 99999,
    debounce_ms = 3000,
    max_file_size = 10000,
    show_progress = true,
    show_progress_every_ms = 5000,
    ai_diagnostics_symbol = "AI",

    use_omniprovider = true,

    use_gemini = false,
    model_gemini = "gemini-2.5-flash-lite",
    fallback_models_gemini = {
        "gemini-2.5-flash", "gemini-3-flash-preview", "gemini-2.5-pro"
    },

    use_openrouter = false,
    model_openrouter = "tngtech/tng-r1t-chimera:free",

    use_groq = false,
    model_groq = "openai/gpt-oss-120b",
    fallback_models_groq = {
        "openai/gpt-oss-20b", "openai/gpt-oss-safeguard-20b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"
    },

    AnalysisSubsystem = {
        write = { "Basic" },
        open = { "Basic" },
        change = {  },
        command = { "Basic" },
        max_threads = 5,
    }
}

---@class user_config
---
---@field api_key_gemini string
---@field api_key_openrouter string
---@field api_key_groq string
---
---@field cmd string[]|nil
---@field filetypes string[]|nil
---@field root_dir function|nil
---@field on_attach function | nil
---@field capabilities lsp.ClientCapabilities | nil
---
---@field timeout number|nil
---@field debounce_ms number|nil
---@field max_file_size number|nil
---@field show_progress boolean|nil
---@field show_progress_every_ms number|nil
---@field ai_diagnostics_symbol string|nil
---
---@field use_omniprovider boolean|nil
---
---@field use_gemini boolean|nil
---@field model_gemini string|nil
---@field fallback_models_gemini string[]|nil
---
---@field use_openrouter boolean|nil
---@field model_openrouter string|nil
---
---@field use_groq boolean|nil
---@field model_groq string|nil
---@field fallback_models_groq string[]|nil
---
---@field AnalysisSubsystem table<"write" | "open" | "change" | "command" | "max_threads", string[] | number> | nil

-- Setup function called by users in their config
---@param user_config user_config
function M.setup(user_config)
    vim.schedule(function ()
        
        local configs = require('lspconfig.configs')
        if user_config.use_gemini == true or user_config.use_omniprovider == true then
            if user_config.api_key_gemini == nil then
                error("For your usage configuration, you must provide a gemini api key !")
            end
        end

        if user_config.use_openrouter == true or user_config.use_omniprovider == true then
            if user_config.api_key_openrouter == nil then
                error("For your usage configuration, you must provide an openrouter api key ! ")
            end
        end

        if user_config.use_groq == true or user_config.use_omniprovider == true then
            if user_config.api_key_groq == nil then
                error("For your useage configuration, you must provide an groq api key !")
            end
        end

        M.config = {
                cmd = user_config.cmd or default_config.cmd,
                filetypes = user_config.filetypes or default_config.filetypes,
                root_dir = user_config.root_dir or default_config.root_dir,
                on_attach = user_config.on_attach or default_config.on_attach,
                capabilities = user_config.capabilities or default_config.capabilities,
                init_options = {},
        }
        local user_config_filled = vim.tbl_deep_extend("force", default_config, user_config)
        local user_config_sanitised = user_config_filled

        user_config_sanitised.root_dir = nil
        user_config_sanitised.capabilities = nil

        for key, value in pairs(user_config_sanitised) do
            M.config.init_options[key] = value
        end

        -- Register the LSP server configuration
        local lspconfig = require("lspconfig")

        -- Define the server if not already defined
        if not configs.ai_diagnos then
            configs.ai_diagnos = {
                default_config = {
                    cmd = M.config.cmd,
                    filetypes = M.config.filetypes,
                    root_dir = M.config.root_dir,
                    settings = {},
                    name = "ai-lsp",
                },
            }
        end

        local cmd_but_string = " "
        for _, i in pairs(M.config.cmd) do
            cmd_but_string = cmd_but_string .. " " .. i
        end

        vim.fn.jobstart(cmd_but_string, {
            
        })

        local config_cmd_works = true

        -- Setup the LSP client
        if config_cmd_works == true then
            lspconfig.ai_diagnos.setup({
                name = "ai-lsp",
                cmd = M.config.cmd,
                filetypes = M.config.filetypes,
                root_dir = M.config.root_dir,
                on_attach = M.config.on_attach,
                capabilities = M.config.capabilities,
                init_options = M.config.init_options,
            })
        end

        if config_cmd_works ~= true then
            lspconfig.ai_diagnos.setup({
                cmd = "../lsp/.venv/bin/python -m ai_diagnos_lsp",
                filetypes = M.config.filetypes,
                root_dir = M.config.root_dir,
                on_attach = M.config.on_attach,
                capabilities = M.config.capabilities,
                init_options = M.config.init_options,
            })
            print("Overrode your custom cmd, due to the fact that it didnt work")
        end

        vim.api.nvim_create_autocmd("LspAttach",{
            callback=function (args)
                local client = vim.lsp.get_client_by_id(args.data.client_id)
                if client then
                    if client.name == "ai-lsp" then

                        local ns = vim.lsp.diagnostic.get_namespace(client.id, true)
                        vim.diagnostic.config({
                            signs = {
                                text = {
                                    [vim.diagnostic.severity.ERROR] = M.config.init_options.ai_diagnostics_symbol,
                                    [vim.diagnostic.severity.WARN]  = M.config.init_options.ai_diagnostics_symbol,
                                    [vim.diagnostic.severity.INFO]  = M.config.init_options.ai_diagnostics_symbol,
                                    [vim.diagnostic.severity.HINT]  = M.config.init_options.ai_diagnostics_symbol,
                                    -- TODO : Add more options on how to display the AI diagnostics
                                },
                            },
                        }, ns)

                        vim.api.nvim_create_user_command("AIAnalyse", function()
                            local uri = vim.lsp.util.make_text_document_params().uri
                            client:exec_cmd({
                                title="Analyse the current buffer with AI, e.g. basic parse.",
                                command="Analyse.Document",
                                arguments={
                                    uri
                                }
                            })
                        end, {})

                        vim.api.nvim_create_user_command("AIClear", function ()
                            local uri = vim.lsp.util.make_text_document_params().uri
                            client:exec_cmd({
                                title="Clear the AI diagnostics on the current buffer",
                                command="Clear.AIDiagnostics",
                                arguments={
                                    uri
                                }
                            })
                        end, {})

                        vim.api.nvim_create_user_command("AIClearAll", function ()
                            client:exec_cmd({
                                title="Clear ALL the AI diagnostics across all documents",
                                command="Clear.AIDiagnostics.All",
                            })
                        end, {})

                    end
                else
                    print(" No LSP client found ")
                end
        end
        })
    end)
end

---@param use_uv boolean
---@param install_to_venv boolean
function M.build(use_uv, install_to_venv)
    vim.schedule(function ()
        if use_uv == true then
            os.execute("cd ../lsp && uv venv && uv sync")
        else
            if install_to_venv == true then
                print("creating a venv and installing the lsp there")
                os.execute("cd ../lsp && python -m venv venv && .venv/bin/python -m pip install .")
            end
            print("installing the lsp without creating a venv")
            os.execute("cd ../lsp && pip install .")
        end
    end)
end

return M
