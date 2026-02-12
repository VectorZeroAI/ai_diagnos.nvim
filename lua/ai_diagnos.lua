local M = {}

-- Setup function called by users in their config
function M.setup(user_config)

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

    local default_config = {
        cmd = { 'ai-diagnos-lsp' },
        filetypes = { 'python', 'go', 'lua' },
        root_dir = require('lspconfig').util.root_pattern('.git'),
        on_attach = nil,
        capabilities = nil,
        timeout = 99999,
        model_openrouter = "tngtech/tng-r1t-chimera:free",
        debounce_ms = 3000,
        max_file_size = 10000,
        show_progress = true,
        show_progress_every_ms = 5000,
        ai_diagnostics_symbol = "AI",
        model_gemini = "gemini-2.5-flash-lite",
        use_gemini = false,
        use_openrouter = false,
        use_omniprovider = true,
        use_groq = false,
        fallback_models_gemini = {
            "gemini-2.5-flash", "gemini-3-flash-preview"
        },
        model_groq = "openai/gpt-oss-120b",
        fallback_models_groq = {
            "openai/gpt-oss-20b", "openai/gpt-oss-safeguard-20b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"
        }


    }
--    M.config = {
--            cmd = user_config.cmd or default_config.cmd,
--            filetypes = user_config.filetypes or default_config.filetypes,
--            root_dir = user_config.root_dir or default_config.root_dir,
--            on_attach = user_config.on_attach or default_config.on_attach,
--            capabilities = user_config.capabilities or default_config.capabilities,
--            init_options = {
--                api_key_openrouter = user_config.api_key_openrouter,
--                api_key_gemini = user_config.api_key_gemini,
--                timeout = user_config.timeout or default_config.timeout,
--                model_openrouter = user_config.model_openrouter or default_config.model_openrouter,
--                debounce_ms = user_config.debounce_ms or default_config.debounce_ms,
--                max_file_size = user_config.max_file_size or default_config.max_file_size,
--                show_progress = user_config.show_progress or default_config.show_progress,
--                show_progress_every_ms = user_config.show_progress_every_ms or default_config.show_progress_every_ms,
--                ai_diagnostics_symbol = user_config.ai_diagnostics_symbol or default_config.ai_diagnostics_symbol,
--                model_gemini = user_config.model_gemini or default_config.model_gemini,
--                use_gemini = user_config.use_gemini or default_config.use_gemini,
--                use_openrouter = user_config.use_openrouter or default_config.use_openrouter,
--                use_omniprovider = user_config.use_omniprovider or default_config.use_omniprovider,
--                fallback_models_gemini = user_config.fallback_models_gemini or default_config.fallback_models_gemini,
--                api_key_groq = user_config.api_key_groq,
--                model_groq = user_config.model_groq or default_config.model_groq,
--                fallback_models_groq = user_config.fallback_models_groq or default_config.fallback_models_groq,
--                use_groq = user_config.use_groq or default_config.use_groq,
--            },
--        }

    M.config = {
            cmd = user_config.cmd or default_config.cmd,
            filetypes = user_config.filetypes or default_config.filetypes,
            root_dir = user_config.root_dir or default_config.root_dir,
            on_attach = user_config.on_attach or default_config.on_attach,
            capabilities = user_config.capabilities or default_config.capabilities,
            init_options = {},
    }
    vim.tbl_deep_extend("force", default_config, user_config)
    for key, value in pairs(user_config) do
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

    -- Setup the LSP client
    local success = pcall(function ()
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
    )
    if success ~= true then
        local script_path = debug.getinfo(1, "S").source:sub(2)
        local my_python = string.format("%s/../python3/.venv/bin/python", script_path)
        lspconfig.ai_diagnos.setup({
            cmd = string.format("%s -m ai_diagnos_lsp", my_python),
            filetypes = M.config.filetypes,
            root_dir = M.config.root_dir,
            settings = M.config.settings,
            on_attach = M.config.on_attach,
            capabilities = M.config.capabilities,
            init_options = M.config.init_options,
        })
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
        


end

function M.build()
    local Job = require('plenary.job')
    local script_path = debug.getinfo(1, "S").source:sub(2)
    local my_python = string.format("%s/../python3/.venv/bin/python", script_path)
    Job:new({
        command=string.format("cd %s/../python3 && python -m venv venv", script_path),
        on_exit=function ()
            Job:new({
                command=string.format("%s -m pip install -e %s/../python3/.", my_python, script_path),
                on_exit=print('Dependancies installed ! ')
            })
        end,
        on_stderr=function()
            print('failed at installing dependancies. ')
            print(string.format("please go to %s and run 'python -m venv venv' and then run '.venv/bin/python -m pip install -e .'"))
            print('On any issues, I am deeply sorry. Open an Issue on github. ')
        end
    })
end

return M
