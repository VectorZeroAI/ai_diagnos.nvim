# ai_diagnos.nvim doc

Its a plugin that provides an AI based LSP like suggestions funktionality.

ai_diagnos.nvim creates a separate namespace, and puts ai generated diagnostics into there.

It uses OpenRouter API for the models, and requires an API key to funktion.

It triggers the regeneration of the AI diagnostics on eery write, or on command.

# Architecture

The Architecture is really straitforward:

on write: send the file with a prompt into OpenRouter API, get the response, validate json shema real quick and then just display it in a separate namespace, so it doesnt interfear with normal LSP diagnostics.

I built this because LSP diagnostics are static and rule based, and although its perfect for syntax, its lacks the understanding of code and runtime behaviour.
                                                           I know that LLMs may also halucinate or yap shit.          
Wich is why I made it so it doesnt interfear with the normal diagnostics from the LSP, as its only used to provide additional insight, that an LSP might miss.                   

## Architecture details:                                                                                              

Commands:
1. AIToggle --> toggles the AI diagnositics on and off     
2. AIClear --> clears all the AI diagnostics               3. AIAnalyse --> forces rediagnosing the file.             4. AIStatus --> Outputs status