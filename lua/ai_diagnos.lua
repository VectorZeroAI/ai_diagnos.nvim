local M = {}

local default_config = {
    cmd = { 'ai-diagnos-lsp' },
    filetypes = { 'python', 'go', 'lua' },
    root_dir = require('lspconfig').util.root_pattern('.git'),
    on_attach = nil,
    capabilities = nil,
    ai_diagnostics_symbol = "AI"
}

 
---@alias analysisTypes "Basic" | "CrossFile" | "BasicLogic" | "CrossFileLogic" | "BasicStyle" | "CrossFileStyle" >| "Deep"
--  TODO : UPDATE THOSE ONCE ANY OF THOSE ARE ACTUALLY DONE

---@class AnalysisSubsystem
---
---@field write analysisTypes[]
---@field open analysisTypes[]
---@field change analysisTypes[]
---@field command analysisTypes[]
---
---@field max_threads number | nil

---@class CrossFileAnalysis
---
---@field scope string[]
---@field max_analysis_depth number | nil
---@field max_string_size_char number | nil

---@class DiagnosticsSubsystem
---
---@field sqlite_db_name string
---@field ttl_until_invalidation number
---@field ttl_until_deletion number
---@field check_ttl_for_deletion number
---@field check_ttl_for_invalidation number

---@class user_config
---
---@field api_key_gemini string |nil
---@field api_key_openrouter string |nil
---@field api_key_groq string |nil
---@field api_key_cerebras string |nil
---@field api_key_huggingface string |nil
---@field api_key_openai string |nil
---@field api_key_claude string |nil
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
---@field use "Openrouter" | "Omniprovider" | "Claude" | "OpenAI" | "gemini" | "groq" | "cerebras" | "huggingface"| nil
---
---@field model_gemini string|nil
---@field fallback_models_gemini string[]|nil
---
---@field model_openrouter string|nil
---
---@field model_groq string|nil
---@field fallback_models_groq string[]|nil
---
---@field model_cerebras string|nil
---@field fallback_models_cerebras string[]|nil
---@field model_huggingface string|nil
---@field model_openai string|nil
---@field model_claude string|nil
---@field AnalysisSubsystem AnalysisSubsystem|nil
---
---@field CrossFileAnalysis CrossFileAnalysis|nil
---
---@field DiagnosticsSubsystem DiagnosticsSubsystem|nil
---
---
---@field plugin_parsers table<string, string>
---@field prompt_overrides table<string, string>

-- Setup function called by users in their config
---@param user_config user_config
function M.setup(user_config)
    vim.schedule(function ()
        
        local configs = require('lspconfig.configs')

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

        -- TODO: IMPLEMENT THE ACTUAL CHECK. 

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

---@param use_uv boolean|nil
---@param install_to_venv boolean|nil
function M.build(use_uv, install_to_venv)
    if use_uv == nil then
        use_uv = false
    end
    if install_to_venv == nil then
        install_to_venv = true
    end
    vim.schedule(function ()
        if use_uv == true then
            if install_to_venv == false then
                os.execute("cd ../lsp && uv sync --active")
            else
                os.execute("cd ../lsp && uv venv && uv sync")
            end
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
