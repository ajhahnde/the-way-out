import pygame
from settings import *


class Wizard(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_assets()

        self.status = 'idle'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

    def load_assets(self):
        path = "assets/wizard/"
        self.animations = {'idle': [], 'walk': []}

        def import_frames(name, frame_count):
            img_path = f"{path}{name}.png"
            sheet = pygame.image.load(img_path).convert_alpha()
            frames = []
            width = sheet.get_width() // frame_count
            height = sheet.get_height()

            for i in range(frame_count):
                rect = pygame.Rect(i * width, 0, width, height)
                surf = sheet.subsurface(rect)
                scaled = pygame.transform.scale(surf, (width * 5, height * 5))
                frames.append(scaled)
            return frames

        self.animations['idle'] = import_frames('D_Idle', 4)
        self.animations['walk'] = import_frames('D_Walk', 6)

    def get_status(self):
        if self.direction.magnitude() == 0:
            self.status = 'idle'
        else:
            self.status = 'walk'

    def get_input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        self.direction.y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])

        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

    def move(self, dt):
        speed = 400
        self.pos += self.direction * speed * dt
        self.rect.topleft = self.pos

    def animate(self, dt):
        current_animation = self.animations[self.status]

        self.frame_index += self.animation_speed * dt
        if self.frame_index >= len(current_animation):
            self.frame_index = 0

        self.image = current_animation[int(self.frame_index)]

    def update(self, dt):
        self.get_input()
        self.get_status()
        self.move(dt)
        self.animate(dt)


""""
class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_assets()

        self.status = 'idle'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

"""
