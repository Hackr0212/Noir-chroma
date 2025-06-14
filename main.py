import gradio as gr
from langchain_chat import LangChainChat
from deepseek_client import DeepSeekClient
import threading
import time

# Initialize chat
chat = LangChainChat()
deepseek = DeepSeekClient()

def get_response(message):
    """Get response from the AI"""
    try:
        # Get response from LangChain
        response = chat.get_response(message)
        return [[message, response]]  # Return as list of lists
    except Exception as e:
        return [[message, f"Error: {str(e)}"]]  # Return error as list of lists

# Create Gradio interface
def create_interface():
    with gr.Blocks(theme=gr.themes.Default()) as demo:
        gr.Markdown("# Noir-chroma: AI Assistant")
        
        with gr.Row():
            chatbot = gr.Chatbot(
                value=[
                    ["Welcome to Noir-chroma! Type your message below to start...", ""]
                ],
                height=400,
                bubble_full_width=False
            )
            
        with gr.Row():
            message = gr.Textbox(
                placeholder="Type your message here...",
                container=False,
                scale=7
            )
            submit_btn = gr.Button("Send", variant="primary")
            
        message.submit(get_response, inputs=[message], outputs=[chatbot])
        submit_btn.click(get_response, inputs=[message], outputs=[chatbot])
    
    return demo

# Run the interface
demo = create_interface()
demo.launch(share=False)

def process_input(text):
    """Process user input and get AI response"""
    try:
        status_label.set_text('Processing...')
        response = chat.get_response(text)
        current_text = chat_box.html_text
        new_text = current_text + '<br><br><b>You:</b><br>' + text + '<br><br><b>AI:</b><br>' + response
        chat_box.html_text = new_text
        chat_box.rebuild()
        status_label.set_text('Ready')
    except Exception as e:
        status_label.set_text(f'Error: {str(e)}')


def update():
    """Update the UI"""
    time_delta = clock.tick(60)/1000.0
    manager.update(time_delta)

def draw():
    """Draw the screen"""
    screen.fill(BACKGROUND_COLOR)
    manager.draw_ui(screen)
    pygame.display.update()

def main():
    """Main game loop"""
    running = True
    while running:
        handle_events()
        update()
        draw()

if __name__ == '__main__':
    main()
