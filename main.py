import pygame
import pygame_gui
import sys
from pygame.locals import *
from langchain_chat import LangChainChat
from deepseek_client import DeepSeekClient
import threading
import time

# Initialize Pygame
pygame.init()

# Constants
WINDOW_SIZE = (800, 600)
BACKGROUND_COLOR = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)

# Set up display
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption('Noir-chroma: AI Assistant')

clock = pygame.time.Clock()
manager = pygame_gui.UIManager(WINDOW_SIZE)

# Initialize chat
chat = LangChainChat()
deepseek = DeepSeekClient()

# Create UI elements
chat_box = pygame_gui.elements.UITextBox(
    html_text='<b>Welcome to Noir-chroma!</b><br>Type your message below to start...',
    relative_rect=pygame.Rect(20, 20, WINDOW_SIZE[0] - 40, WINDOW_SIZE[1] - 160),
    manager=manager
)

input_box = pygame_gui.elements.UITextEntryLine(
    relative_rect=pygame.Rect(20, WINDOW_SIZE[1] - 120, WINDOW_SIZE[0] - 220, 40),
    manager=manager
)

send_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(WINDOW_SIZE[0] - 180, WINDOW_SIZE[1] - 120, 160, 40),
    text='Send',
    manager=manager
)

status_label = pygame_gui.elements.UILabel(
    relative_rect=pygame.Rect(20, WINDOW_SIZE[1] - 80, WINDOW_SIZE[0] - 40, 30),
    text='Ready',
    manager=manager
)

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

def handle_events():
    """Handle Pygame events"""
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == send_button:
                text = input_box.get_text().strip()
                if text:
                    input_box.set_text('')
                    threading.Thread(target=process_input, args=(text,)).start()

        manager.process_events(event)

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
