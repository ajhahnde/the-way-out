import pygame
from settings import *
from units import Wizard
from lvls import *


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, color=(100, 100, 100), is_exit=False):
        super().__init__(groups)
        self.image = pygame.Surface((64, 64))  # Größe eines Blocks (Tilesize)
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=pos)
        self.is_exit = is_exit


class LevelManager:
    def __init__(self):
        self.current_level_index = 0
        self.levels = [Level1(), Level2()]  # Liste aller Level
        self.current_level = self.levels[self.current_level_index]

    def setup_level(self):
        self.current_level.setup()

    def update(self, dt):
        return self.current_level.update(dt)

    def draw(self, screen):
        self.current_level.draw(screen)

    def next_level(self):
        self.current_level_index += 1
        if self.current_level_index < len(self.levels):
            self.current_level = self.levels[self.current_level_index]
            self.current_level.setup()
        else:
            print("Spiel gewonnen! Keine Level mehr.")
            # Hier könnte man zurück ins Hauptmenü springen

# --- Basis-Level-Logik ---


class GameLevel:
    def __init__(self):
        self.visible_sprites = pygame.sprite.Group()
        self.obstacle_sprites = pygame.sprite.Group()  # Mauern
        self.exit_sprites = pygame.sprite.Group()     # Türen
        self.player = None
        self.finished = False

    def create_map(self, layout):
        # Layout ist eine Liste von Strings (die Karte)
        TILE_SIZE = 64
        self.visible_sprites.empty()
        self.obstacle_sprites.empty()
        self.exit_sprites.empty()

        for row_index, row in enumerate(layout):
            for col_index, cell in enumerate(row):
                x = col_index * TILE_SIZE
                y = row_index * TILE_SIZE

                if cell == '#':
                    Tile((x, y), [self.visible_sprites,
                         self.obstacle_sprites], color=(100, 100, 100))

                elif cell == 'E':
                    Tile((x, y), [self.visible_sprites, self.exit_sprites], color=(
                        0, 255, 0), is_exit=True)

                elif cell == 'P':
                    # Spieler erstellen
                    self.player = Wizard(x, y)
                    self.visible_sprites.add(self.player)

    def update(self, dt):
        self.visible_sprites.update(dt)
        self.check_collisions()
        return self.finished  # Gibt True zurück, wenn Level vorbei ist

    def check_collisions(self):
        if self.player:
            # 1. Kollision mit Wänden (damit man nicht durchläuft)
            # Hinweis: Das ist eine simple Box-Kollision.
            # Für perfekte Physik müsste man x und y getrennt prüfen (wie im ersten Skript).
            hits = pygame.sprite.spritecollide(
                self.player, self.obstacle_sprites, False)
            if hits:
                # Simpler "Push back" - verhindert durchlaufen (kann verbessert werden)
                self.player.pos -= self.player.direction * 10
                self.player.rect.topleft = self.player.pos

            # 2. Kollision mit Ausgang
            exit_hit = pygame.sprite.spritecollideany(
                self.player, self.exit_sprites)
            if exit_hit:
                self.finished = True  # Signal an Main: Level fertig!

    def draw(self, screen):
        self.visible_sprites.draw(screen)
