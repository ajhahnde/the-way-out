import pygame
import sys
from settings import *
from units import Wizard
from menu import MainMenu, SettingsMenu

pygame.init()

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.SCALED)
clock = pygame.time.Clock()

main_menu = MainMenu(WIDTH, HEIGHT)
settings_menu = SettingsMenu(WIDTH, HEIGHT)

all_sprites = pygame.sprite.Group()
player = Wizard(WIDTH / 2, HEIGHT / 2)
all_sprites.add(player)

game_state = "menu"
running = True

while running:
    dt = clock.tick(FPS) / 1000.0

    # --- Events ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if game_state == "game":
                game_state = "menu"
            elif game_state == "settings":
                game_state = "menu"

        if game_state == "menu":
            action = main_menu.handle_input(event)
            if action == "game":
                game_state = "game"
            elif action == "settings":
                game_state = "settings"
            elif action == "quit":
                running = False

        elif game_state == "settings":
            action = settings_menu.handle_input(event)
            if action == "back":
                game_state = "menu"

    if game_state == "menu":
        main_menu.draw(screen)

    elif game_state == "settings":
        settings_menu.draw(screen)

    elif game_state == "game":
        all_sprites.update(dt)
        screen.fill(BLACK)
        all_sprites.draw(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
