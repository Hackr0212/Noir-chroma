import speech_recognition as sr
from rich.console import Console
from rich.prompt import Prompt
from langchain_chat import LangChainChat
from deepseek_client import DeepSeekClient

console = Console()
chat = LangChainChat()
deepseek = DeepSeekClient()

console.print("[bold]Noir-chroma: Voice & Text Input Demo[/bold]")
console.print("You can enter text or use your microphone to input speech.")

while True:
    choice = Prompt.ask("Choose input method", choices=["text", "speech", "quit"])
    
    if choice == "text":
        text = Prompt.ask("Enter your message")
        console.print(f"[green]Text input:[/green] {text}")
        
        # Process with LangChain and Deepseek
        console.print("[yellow]Processing your request...[/yellow]")
        response = chat.get_response(text)
        console.print(f"[blue]AI Response:[/blue] {response}")
        
    elif choice == "speech":
        console.print("[yellow]Listening...[/yellow]")
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio)
                console.print(f"[green]Speech input:[/green] {text}")
                
                # Process with LangChain and Deepseek
                console.print("[yellow]Processing your request...[/yellow]")
                response = chat.get_response(text)
                console.print(f"[blue]AI Response:[/blue] {response}")
            except sr.UnknownValueError:
                console.print("[red]Could not understand audio[/red]")
            except sr.RequestError as e:
                console.print(f"[red]Could not request results; {e}[/red]")
    
    elif choice == "quit":
        break

# --- Future Integration Points ---
# - Integrate AI response logic here
# - Add Live2D/avatar display if desired
# - Add more advanced UI features as needed
