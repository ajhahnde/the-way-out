import pygame
from pygame.sprite import _Group


class Door(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_assets()
        # Door & Big Door & Trapdoor

    def load_assets(self):
        pass


class Chest(pygame.sprite.Sprite):
    pass
    # Chest 1 & Chest2


class Fire(pygame.sprite.Sprite):
    pass


class Lever(pygame.sprite.Sprite):
    pass
    # Lever 1 & Lever 2


class Spikes(pygame.sprite.Sprite):
    pass
