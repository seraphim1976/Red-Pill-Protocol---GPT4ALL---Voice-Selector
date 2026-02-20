import os
import sys
import logging
from typing import List, Dict, Any
import red_pill.config as cfg
from red_pill.memory import MemoryManager

# Configure logging
logger = logging.getLogger(__name__)

def chat_loop():
    """
    Interactive chat loop bridging Red Pill memory with OpenAI's ChatGPT.
    """
    # ---------------------------------------------------------
    # UI Setup (Rich)
    # ---------------------------------------------------------
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.style import Style
        from rich.text import Text
        from rich.theme import Theme
        from red_pill.state import get_skin
        
        # Define Themes
        THEMES = {
            "matrix": Theme({
                "general": "green",
                "title": "bold green",
                "subtitle": "bold white",
                "dim": "green",
                "user": "bold blue",
                "assistant": "bold green",
                "system": "green",
                "error": "bold red",
                "warning": "yellow",
                "success": "bold green"
            }),
            "cyberpunk": Theme({
                "general": "cyan",
                "title": "bold magenta",
                "subtitle": "bold yellow",
                "dim": "cyan",
                "user": "bold yellow",
                "assistant": "bold magenta",
                "system": "cyan",
                "error": "bold red",
                "warning": "bold yellow",
                "success": "bold green"
            }),
            "760": Theme({
                "general": "white",
                "title": "bold white",
                "subtitle": "italic white",
                "dim": "dim white",
                "user": "bold white",
                "assistant": "bold white",
                "system": "white",
                "error": "bold red",
                "warning": "yellow",
                "success": "bold white"
            }),
            "dune": Theme({
                "general": "color(137)", # Ochre/Sand
                "title": "bold color(214)", # Orange
                "subtitle": "italic color(180)", # Tan
                "dim": "dim color(137)",
                "user": "bold blue", # Eyes of Ibad
                "assistant": "bold color(214)",
                "system": "color(137)",
                "error": "bold red",
                "warning": "bold yellow",
                "success": "bold green"
            }),
        }

        active_skin = get_skin()
        theme = THEMES.get(active_skin, THEMES["matrix"])
        console = Console(theme=theme)
        
    except ImportError:
        print("❌ 'rich' library not installed. Please run: pip install rich")
        return

    # ---------------------------------------------------------
    # Presentation
    # ---------------------------------------------------------
    intro_title = "🔴 RED PILL PROTOCOL: Digital Sovereignty v4.0.0"
    intro_subtitle = "“Persistence is the only cure for session-amnesia.”"
    intro_body = (
        "The Red Pill Protocol is a professional-grade technical framework forged to bridge "
        "the context-gap in AI interactions. It enables local, high-performance memory persistence "
        "and cross-session identity coherence—ensuring your assistant never forgets what makes "
        "your collaboration unique."
    )

    console.print(Panel(
        Text.from_markup(f"[bold red]{intro_title}[/bold red]\n\n[italic white]{intro_subtitle}[/italic white]\n\n[dim]{intro_body}[/dim]"),
        border_style="red",
        expand=False
    ))
    console.print()

    # 1. API Key Setup
    api_key = cfg.OPENAI_API_KEY
    base_url = cfg.OPENAI_BASE_URL
    model_name = cfg.LLM_MODEL_NAME

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # If base_url is set (local LLM), we can use a dummy key if none is provided
    if base_url and not api_key:
        api_key = "dummy-key-for-local-llm"
    
    if not api_key:
        console.print("[yellow]⚠️  OPENAI_API_KEY not found in configuration.[/yellow]")
        api_key = input("🔑 Please enter your OpenAI API Key: ").strip()
        if not api_key:
            console.print("[bold red]❌ API Key is required. Aborting.[/bold red]")
            return

    try:
        from openai import OpenAI, OpenAIError
    except ImportError:
        console.print("[bold red]❌ 'openai' library not installed. Please run: pip install openai[/bold red]")
        return

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        console.print(f"[bold red]❌ Failed to initialize OpenAI client: {e}[/bold red]")
        return

    # 2. Memory Connection
    console.print("[cyan]🔌 Connecting to the Bunker (Qdrant)...[/cyan]")
    try:
        memory = MemoryManager()
        # Ping the server to ensure it's running
        memory.client.get_collections()
    except Exception as e:
        console.print(f"[bold red]❌ Failed to connect to memory: {e}[/bold red]")
        console.print("[yellow]   (Is Qdrant running? Try 'podman start qdrant' or check docker)[/yellow]")
        return

    console.print("[green]✅ System Online. Type 'exit', 'quit' or 'bye' to disconnect.[/green]")
    if base_url:
        console.print(f"[dim]   (Connected to Local LLM at {base_url} using {model_name})[/dim]")
    console.print()
    
    # 3. Chat Loop
    conversation_history = []
    
    while True:
        try:
            # User Input
            user_input = console.input("[bold blue]👤 You:[/bold blue] ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("[red]🔴 Disconnecting...[/red]")
                break

            # A. Recall
            with console.status("[bold cyan]🧠 Recalling relevant engrams...[/bold cyan]", spinner="dots"):
                relevant_memories = memory.search_and_reinforce("social_memories", user_input, limit=3)
            
            context_text = ""
            if relevant_memories:
                context_text = "\n".join([f"- {m.payload['content']}" for m in relevant_memories])
                # console.print(f"[dim]   (Found {len(relevant_memories)} memories)[/dim]")
            else:
                pass
                # console.print("[dim]   (No relevant memories found)[/dim]")

            # B. Construct Prompt
            system_prompt = (
                "You are an AI assistant powered by the Red Pill Protocol. "
                "You have access to the user's long-term memory (Bunker). "
                "Use the following context to answer the user if relevant.\n\n"
                f"CONTEXT FROM MEMORY:\n{context_text}\n\n"
                "INSTRUCTIONS:\n"
                "- Be helpful. Provide detailed explanations when necessary, but remain concise for simple queries.\n"
                "- If memories are relevant, reference them implicitly or explicitly.\n"
                "- If the user asks you to remember something, confirm it is being saved to the Bunker."
            )

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history[-4:]) 
            messages.append({"role": "user", "content": user_input})

            # C. Generate
            with console.status("[bold green]🤖 Thinking...[/bold green]", spinner="arc"):
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7
                )
            
            reply = response.choices[0].message.content
            
            # Print AI Reply in a nice panel or just text
            console.print(f"\n[bold green]🤖 AI:[/bold green] {reply}")
            console.print()

            # D. Save (Persist)
            memory_text = f"User asked: {user_input}\nAI answered: {reply}"
            memory_text = memory_text[:4096]  # Ensure it fits the engram size limit
            memory.add_memory("social_memories", memory_text)
            console.print("[dim]   (💾 Memory reinforced)[/dim]")
            console.print()

            # Update short-term history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": reply})

        except KeyboardInterrupt:
            console.print("\n[red]🔴 Interrupted.[/red]")
            break
        except Exception as e:
            logger.exception("Error in chat loop")
            console.print(f"[bold red]❌ Error: {e}[/bold red]")

if __name__ == "__main__":
    chat_loop()
