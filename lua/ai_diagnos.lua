-- lua/ai-diagnostics/init.lua

local M = {}
local api = vim.api
local uv = vim.loop

-- Dedicated namespace for AI diagnostics
local ns_id = api.nvim_create_namespace("ai_diagnostics")

-- Default configuration
local config = {
    api_key = "",
    model = "anthropic/claude-3.5-sonnet",
    enabled = true,
    debounce_ms = 2000,
    max_file_size = 10000,
    timeout_ms = 30000,
    show_progress = true,
}

-- Active state tracking
local state = {
    pending_buffers = {},
    active_jobs = {},
    timers = {},
}

-- Anchor resolution helper
local function find_anchor_positions(bufnr, start_anchor, end_anchor)
    local lines = api.nvim_buf_get_lines(bufnr, 0, -1, false)
    local text = table.concat(lines, "\n")

    -- Find start and end anchors as literal substrings
    local start_pos = text:find(start_anchor, 1, true)
    if not start_pos then
        return nil, "start_anchor not found"
    end

    -- Search for end_anchor after start_pos; allow end_anchor to be identical to start_anchor
    local end_pos = text:find(end_anchor, start_pos, true)
    if not end_pos then
        return nil, "end_anchor not found"
    end

    -- Convert absolute byte offsets to line/col (1-indexed lines, 0-indexed cols)
    local function offset_to_linecol(offset)
        -- offset is 1-based byte index into text
        local pre_text = text:sub(1, offset - 1)
        local lnum = #vim.split(pre_text, "\n")
        local last_line = pre_text:match("([^\n]*)$") or ""
        local col = #last_line
        return lnum, col
    end

    local start_lnum, start_col = offset_to_linecol(start_pos)
    local end_lnum, end_col = offset_to_linecol(end_pos + #end_anchor - 1)

    -- Ensure we return 0-indexed line numbers for diagnostics API (lnum is 0-indexed)
    return {
        lnum = start_lnum - 1,
        col = start_col,
        end_lnum = end_lnum - 1,
        end_col = end_col + 1, -- make end_col exclusive where possible
    }, nil
end

-- Parse response with anchors
local function parse_response(bufnr, response_text)
    local ok, decoded = pcall(vim.json.decode, response_text)
    if not ok then
        return nil, "Invalid JSON response"
    end

    if type(decoded.diagnostics) ~= "table" then
        return nil, "Response missing 'diagnostics' array"
    end

    local diagnostics = {}
    for _, diag in ipairs(decoded.diagnostics) do
        -- Validate required fields
        if type(diag.start_anchor) ~= "string" or type(diag.end_anchor) ~= "string" then
            -- skip invalid diagnostic entries
        else
            local range, find_err = find_anchor_positions(bufnr, diag.start_anchor, diag.end_anchor)
            if not range then
                -- If anchors not found, skip this diagnostic but continue processing others
            else
                local severity_map = {
                    error = vim.diagnostic.severity.ERROR,
                    warning = vim.diagnostic.severity.WARN,
                    info = vim.diagnostic.severity.INFO,
                    hint = vim.diagnostic.severity.HINT,
                }
                local sev = severity_map[diag.severity] or vim.diagnostic.severity.INFO

                table.insert(diagnostics, {
                    lnum = range.lnum,
                    col = range.col,
                    end_lnum = range.end_lnum,
                    end_col = range.end_col,
                    severity = sev,
                    message = diag.message or "",
                    code = diag.code,
                    source = "ai-diagnostics",
                })
            end
        end
    end

    return diagnostics, nil
end

-- Cancel any pending job for a buffer
local function cancel_job(bufnr)
    if state.timers[bufnr] then
        pcall(function()
            state.timers[bufnr]:stop()
            state.timers[bufnr]:close()
        end)
        state.timers[bufnr] = nil
    end

    if state.active_jobs[bufnr] then
        if state.active_jobs[bufnr].handle then
            pcall(uv.process_kill, state.active_jobs[bufnr].handle, 15)
        end
        state.active_jobs[bufnr] = nil
    end

    state.pending_buffers[bufnr] = nil
end

-- Async HTTP POST using curl via libuv
local function async_http_post(url, headers, body, callback)
    local stdout_chunks = {}
    local stderr_chunks = {}

    local header_args = {}
    for _, header in ipairs(headers) do
        table.insert(header_args, "-H")
        table.insert(header_args, header)
    end

    local args = vim.list_extend({
        "-s", "-X", "POST", url,
        "-d", body
    }, header_args)

    local stdout = uv.new_pipe(false)
    local stderr = uv.new_pipe(false)

    local handle, pid = uv.spawn("curl", {
        args = args,
        stdio = {nil, stdout, stderr}
    }, function(code, signal)
        if stdout then stdout:close() end
        if stderr then stderr:close() end
        vim.schedule(function()
            if code == 0 then
                local response = table.concat(stdout_chunks)
                callback(nil, response)
            else
                local error_msg = table.concat(stderr_chunks)
                callback("Request failed with code " .. tostring(code) .. ": " .. error_msg, nil)
            end
        end)
    end)

    if not handle then
        if stdout then stdout:close() end
        if stderr then stderr:close() end
        callback("Failed to spawn curl process (curl not found?)", nil)
        return nil
    end

    uv.read_start(stdout, function(err, data)
        if data then
            table.insert(stdout_chunks, data)
        end
    end)

    uv.read_start(stderr, function(err, data)
        if data then
            table.insert(stderr_chunks, data)
        end
    end)

    return handle, pid
end

-- Build structured prompt for LLM
local function build_prompt(content, filetype)
    return string.format([[You are a code analysis tool. Analyze the following %s code and identify potential issues.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
    "diagnostics": [
        {
            "start_anchor": "<verbatim snippet start>",
            "end_anchor": "<verbatim snippet end>",
            "severity": "<error|warning|info|hint>",
            "message": "<description>",
            "code": "<optional_code>"
        }
    ]
}

Rules:
- Anchors must be verbatim substrings from the code
- Anchors should be short but unique; prefer including surrounding context to avoid duplicates
- severity must be exactly: error, warning, info, or hint
- Focus on bugs, performance issues, and best practice violations
- If no issues found, return {"diagnostics": []}

Code to analyze:
%s]], filetype, content)
end

-- Main analysis function
local function analyze_buffer(bufnr)
    if not config.enabled then return end
    if not api.nvim_buf_is_valid(bufnr) then return end

    if not config.api_key or config.api_key == "" then
        vim.notify("AI Diagnostics: API key not configured", vim.log.levels.ERROR)
        return
    end

    local lines = api.nvim_buf_get_lines(bufnr, 0, -1, false)
    if #lines > config.max_file_size then
        vim.notify(string.format("AI Diagnostics: File too large (%d lines, max %d)",
            #lines, config.max_file_size), vim.log.levels.WARN)
        return
    end

    local content = table.concat(lines, "\n")
    local filetype = vim.bo[bufnr].filetype or "text"

    if config.show_progress then
        vim.notify("AI Diagnostics: Analyzing...", vim.log.levels.INFO)
    end

    local prompt = build_prompt(content, filetype)
    local request_body = vim.json.encode({
        model = config.model,
        messages = {{role = "user", content = prompt}},
        temperature = 0.1,
    })

    local headers = {
        "Authorization: Bearer " .. config.api_key,
        "Content-Type: application/json",
        "HTTP-Referer: neovim-ai-diagnostics",
    }

    -- Set timeout
    local timeout_timer = uv.new_timer()
    local timed_out = false

    timeout_timer:start(config.timeout_ms, 0, function()
        timed_out = true
        cancel_job(bufnr)
        vim.schedule(function()
            vim.notify("AI Diagnostics: Request timed out", vim.log.levels.WARN)
        end)
    end)

    local handle, pid = async_http_post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers,
        request_body,
        function(err, response)
            -- stop and close timer safely
            pcall(function()
                timeout_timer:stop()
                timeout_timer:close()
            end)

            if timed_out then return end

            state.active_jobs[bufnr] = nil

            if err then
                vim.schedule(function()
                    vim.notify("AI Diagnostics: " .. err, vim.log.levels.ERROR)
                end)
                return
            end

            local ok, decoded = pcall(vim.json.decode, response)
            if not ok then
                vim.schedule(function()
                    vim.notify("AI Diagnostics: Failed to parse API response", vim.log.levels.ERROR)
                end)
                return
            end

            if decoded.error then
                vim.schedule(function()
                    vim.notify("AI Diagnostics: API error - " .. (decoded.error.message or "unknown"),
                        vim.log.levels.ERROR)
                end)
                return
            end

            if not decoded.choices or not decoded.choices[1] or not decoded.choices[1].message then
                vim.schedule(function()
                    vim.notify("AI Diagnostics: Unexpected API response format", vim.log.levels.ERROR)
                end)
                return
            end

            local content = decoded.choices[1].message.content
            local diagnostics, parse_err = parse_response(bufnr, content)

            if parse_err then
                vim.schedule(function()
                    vim.notify("AI Diagnostics: " .. parse_err, vim.log.levels.ERROR)
                end)
                return
            end

            if not api.nvim_buf_is_valid(bufnr) then return end

            -- Convert diagnostics into the format expected by vim.diagnostic.set
            -- Each diagnostic should include range fields: lnum, col, end_lnum, end_col
            vim.schedule(function()
                vim.diagnostic.set(ns_id, bufnr, diagnostics, {})
                if config.show_progress then
                    if #diagnostics > 0 then
                        vim.notify(string.format("AI Diagnostics: Found %d issue(s)", #diagnostics),
                            vim.log.levels.INFO)
                    else
                        vim.notify("AI Diagnostics: No issues found", vim.log.levels.INFO)
                    end
                end
            end)
        end
    )

    if handle then
        state.active_jobs[bufnr] = {handle = handle, pid = pid}
    end
end

-- Debounced analysis with cancellation
local function schedule_analysis(bufnr)
    cancel_job(bufnr)

    local timer = uv.new_timer()
    state.timers[bufnr] = timer

    timer:start(config.debounce_ms, 0, function()
        pcall(function()
            timer:stop()
            timer:close()
        end)
        state.timers[bufnr] = nil
        vim.schedule(function()
            analyze_buffer(bufnr)
        end)
    end)
end

function M.setup(opts)
    config = vim.tbl_deep_extend("force", config, opts or {})

    if not config.api_key or config.api_key == "" then
        vim.notify("AI Diagnostics: Warning - API key not set", vim.log.levels.WARN)
    end

    -- Set up custom highlight for AI diagnostics (purple)
    vim.cmd([[
        highlight DiagnosticSignAI guifg=#9d7cd8 ctermfg=141
        highlight DiagnosticVirtualTextAI guifg=#9d7cd8 ctermfg=141
    ]])

    -- Define custom signs with "AI" text
    vim.fn.sign_define("DiagnosticSignAIError", {
        text = "AI",
        texthl = "DiagnosticSignAI",
        numhl = "DiagnosticSignAI"
    })
    vim.fn.sign_define("DiagnosticSignAIWarn", {
        text = "AI",
        texthl = "DiagnosticSignAI",
        numhl = "DiagnosticSignAI"
    })
    vim.fn.sign_define("DiagnosticSignAIInfo", {
        text = "AI",
        texthl = "DiagnosticSignAI",
        numhl = "DiagnosticSignAI"
    })
    vim.fn.sign_define("DiagnosticSignAIHint", {
        text = "AI",
        texthl = "DiagnosticSignAI",
        numhl = "DiagnosticSignAI"
    })

    -- Configure diagnostics to use our custom signs
    vim.diagnostic.config({
        signs = {
            severity = {
                min = vim.diagnostic.severity.HINT,
                max = vim.diagnostic.severity.ERROR,
            },
            -- Use virtual text highlight group for virtual text
            virtual_text = {
                prefix = "●",
                severity = vim.diagnostic.severity.ERROR,
                spacing = 2,
            },
        },
    }, ns_id)

    local group = api.nvim_create_augroup("AIDiagnostics", {clear = true})

    api.nvim_create_autocmd("BufWritePost", {
        group = group,
        callback = function(args)
            if config.enabled then
                schedule_analysis(args.buf)
            end
        end
    })

    api.nvim_create_autocmd("BufDelete", {
        group = group,
        callback = function(args)
            cancel_job(args.buf)
            vim.diagnostic.reset(ns_id, args.buf)
        end
    })

    -- Commands
    api.nvim_create_user_command("AIToggle", function()
        config.enabled = not config.enabled
        vim.notify("AI Diagnostics: " .. (config.enabled and "Enabled" or "Disabled"),
            vim.log.levels.INFO)
    end, {})

    api.nvim_create_user_command("AIClear", function()
        local bufnr = api.nvim_get_current_buf()
        cancel_job(bufnr)
        vim.diagnostic.reset(ns_id, bufnr)
        vim.notify("AI Diagnostics: Cleared", vim.log.levels.INFO)
    end, {})

    api.nvim_create_user_command("AIAnalyze", function()
        local bufnr = api.nvim_get_current_buf()
        cancel_job(bufnr)
        analyze_buffer(bufnr)
    end, {})

    api.nvim_create_user_command("AIStatus", function()
        local status_lines = {
            "AI Diagnostics Status:",
            "    Enabled: " .. tostring(config.enabled),
            "    Model: " .. config.model,
            "    Debounce: " .. config.debounce_ms .. "ms",
            "    Max file size: " .. config.max_file_size .. " lines",
            "    Active jobs: " .. vim.tbl_count(state.active_jobs),
            "    Pending timers: " .. vim.tbl_count(state.timers),
        }
        vim.notify(table.concat(status_lines, "\n"), vim.log.levels.INFO)
    end, {})
end

return M
