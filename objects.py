import pygame
from pygame.sprite import _Group


class Portal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_assets()

    def load_assets(self):
        pass
