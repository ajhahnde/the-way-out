import pygame
import sys
from settings import *
from menu import MainMenu, SettingsMenu, LevelMenu, CharacterMenu
from levels import LevelManager

# Setup & Initalisation
pygame.init()
screen = pygame.display.set_mode(
    (WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.SCALED)
clock = pygame.time.Clock()

main_menu = MainMenu(WIDTH, HEIGHT)
settings_menu = SettingsMenu(WIDTH, HEIGHT)
level_menu = LevelMenu(WIDTH, HEIGHT)
character_menu = CharacterMenu(WIDTH, HEIGHT)
level_manager = LevelManager(WIDTH, HEIGHT)

# Game loop
game_state = "menu"
current_character = "c_wiz"

running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if game_state == "lvls":
                game_state = "menu"
            elif game_state == "settings":
                game_state = "menu"
            elif game_state == "char_select":
                game_state = "menu"
            elif game_state == "game":
                game_state = "lvls"

        # Main menu
        if game_state == "menu":
            action = main_menu.handle_input(event)
            if action == "lvls":
                game_state = "lvls"
            elif action == "settings":
                game_state = "settings"
            elif action == "chars":
                game_state = "char_select"
            elif action == "quit":
                running = False

        # Settings
        elif game_state == "settings":
            action = settings_menu.handle_input(event)
            if action == "back":
                game_state = "menu"

        # Charakter select
        elif game_state == "char_select":
            action = character_menu.handle_input(event)
            if action:
                current_character = action
                game_state = "menu"

        # Levels select
        elif game_state == "lvls":
            action = level_menu.handle_input(event)
            if action == "level1":
                level_manager.load_level(0, current_character)
                game_state = "game"
            elif action == "level2":
                level_manager.load_level(1, current_character)
                game_state = "game"
            elif action == "level3":
                level_manager.load_level(2, current_character)
                game_state = "game"

    # Draw & Update
    if game_state == "menu":
        main_menu.draw(screen)
    elif game_state == "settings":
        settings_menu.draw(screen)
    elif game_state == "char_select":
        character_menu.draw(screen, current_character)
    elif game_state == "lvls":
        level_menu.draw(screen)
    elif game_state == "game":
        level_manager.update(dt)
        level_manager.draw(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
