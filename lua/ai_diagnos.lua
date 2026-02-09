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
        timeout_ms = 99999,
        model = "tngtech/tng-r1t-chimera:free",
        debounce_ms = 3000,
        max_file_size = 10000,
        show_progress = true,
        show_progress_every_ms = 1000,
        ai_diagnostics_symbol = "AI",
    }
    M.config = {
            cmd = user_config.cmd or default_config.cmd,
            filetypes = user_config.filetypes or default_config.filetypes,
            root_dir = user_config.root_dir or default_config.root_dir,
            settings = user_config.settings or default_config.settings,
            on_attach = user_config.on_attach or default_config.on_attach,
            capabilities = user_config.capabilities or default_config.capabilities,
            init_options = {
                api_key = user_config.api_key,
                timeout_ms = user_config.timeout_ms or default_config.timeout_ms,
                model = user_config.model or default_config.model,
                debounce_ms = user_config.debounce_ms or default_config.debounce_ms,
                max_file_size = user_config.max_file_size or default_config.max_file_size,
                show_progress = user_config.show_progress or default_config.show_progress,
                show_progress_every_ms = user_config.show_progress_every_ms or default_config.show_progress_every_ms,
            },
            ai_diagnostics_symbol = user_config.ai_diagnostics_symbol or default_config.ai_diagnostics_symbol,
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

    local ai_ns = vim.api.nvim_create_namespace("ai_lsp_diagnostics")

    lspconfig.ai_diagnos.setup({
        handlers = {
            -- Handle pull diagnostics response
            ["textDocument/diagnostic"] = function(err, result, ctx, config)
                if err then return end

                local client = vim.lsp.get_client_by_id(ctx.client_id)
                local bufnr = ctx.bufnr
                -- Extract diagnostics from result
                --
                local diagnostics = result.items or result.relatedDocuments or {}
                -- Set to custom namespace with custom signs
                --
                vim.diagnostic.set(ai_ns, bufnr, diagnostics)
                -- Configure for this namespace
                --
                -- TODO : Try to asign ai_diagnostics_symbol[1] [2] [3] [4] , if fail, do what it does now
                --
                vim.diagnostic.config({
                    signs = {
                        text = {
                            [vim.diagnostic.severity.ERROR] = M.config.ai_diagnostics_symbol,
                            [vim.diagnostic.severity.WARN] = M.config.ai_diagnostics_symbol,
                            [vim.diagnostic.severity.HINT] = M.config.ai_diagnostics_symbol,
                            [vim.diagnostic.severity.INFO] = M.config.ai_diagnostics_symbol,
                        }
                    },
                }, ai_ns)
            end,
        },
    })
  
    -- Setup the LSP client
    local success = pcall(function ()
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

    vim.api.nvim_create_user_command("AIAnalyse", function()
        local params = {
          uri = vim.uri_from_bufnr(0)  -- Current buffer URI
        }
        vim.cmd(string.format("LspCommand Analyse.Document %s", params))
    end, {})

    vim.api.nvim_create_user_command("AIClear", function ()
        vim.cmd("LspCommand Clear.AIDiagnostics")
    end, {})
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
