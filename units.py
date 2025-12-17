import pygame
from settings import *


class Wizard(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.facing = 'down'
        self.load_assets()

        self.status = 'idle_down'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

    def load_assets(self):
        path = "assets/wizard/"

        self.animations = {
            'idle_down': [], 'walk_down': [],
            'idle_up': [], 'walk_up': [],
            'idle_left': [], 'walk_left': [],
            'idle_right': [], 'walk_right': []
        }

        def import_frames(name, frame_count):
            img_path = f"{path}{name}.png"
            try:
                sheet = pygame.image.load(img_path).convert_alpha()
            except FileNotFoundError:
                print(f"{img_path} not found.")
                return []  # crash safty

            frames = []
            width = sheet.get_width() // frame_count
            height = sheet.get_height()

            for i in range(frame_count):
                rect = pygame.Rect(i * width, 0, width, height)
                surf = sheet.subsurface(rect)
                scaled = pygame.transform.scale(surf, (width * 5, height * 5))
                frames.append(scaled)
            return frames

        # DOWN
        self.animations['idle_down'] = import_frames('D_Idle', 4)
        self.animations['walk_down'] = import_frames('D_Walk', 6)

        # UP
        self.animations['idle_up'] = import_frames('U_Idle', 4)
        self.animations['walk_up'] = import_frames('U_Walk', 6)

        # LEFT
        self.animations['idle_left'] = import_frames('S_Idle', 4)
        self.animations['walk_left'] = import_frames('S_Walk', 6)

        # RIGHT
        self.animations['idle_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['idle_left']
        ]
        self.animations['walk_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['walk_left']
        ]

    def get_status(self):
        if self.direction.magnitude() != 0:
            if abs(self.direction.x) > abs(self.direction.y):
                if self.direction.x > 0:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
            else:
                if self.direction.y > 0:
                    self.facing = 'down'
                else:
                    self.facing = 'up'

        if self.direction.magnitude() == 0:
            self.status = f'idle_{self.facing}'
        else:
            self.status = f'walk_{self.facing}'

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

        if not current_animation:
            return

        self.frame_index += self.animation_speed * dt
        if self.frame_index >= len(current_animation):
            self.frame_index = 0

        self.image = current_animation[int(self.frame_index)]

    def update(self, dt):
        self.get_input()
        self.get_status()
        self.move(dt)
        self.animate(dt)


class Penguin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.facing = 'down'
        self.load_assets()

        self.status = 'idle_down'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

    def load_assets(self):
        path = "assets/penguin/"

        self.animations = {
            'idle_down': [], 'walk_down': [],
            'idle_up': [], 'walk_up': [],
            'idle_left': [], 'walk_left': [],
            'idle_right': [], 'walk_right': []
        }

        def import_frames(name, frame_count):
            img_path = f"{path}{name}.png"
            try:
                sheet = pygame.image.load(img_path).convert_alpha()
            except FileNotFoundError:
                print(f"{img_path} not found.")
                return []  # crash safty

            frames = []
            width = sheet.get_width() // frame_count
            height = sheet.get_height()

            for i in range(frame_count):
                rect = pygame.Rect(i * width, 0, width, height)
                surf = sheet.subsurface(rect)
                scaled = pygame.transform.scale(surf, (width * 5, height * 5))
                frames.append(scaled)
            return frames

        # DOWN
        self.animations['idle_down'] = import_frames('D_Idle', 4)
        self.animations['walk_down'] = import_frames('D_Walk', 6)

        # UP
        self.animations['idle_up'] = import_frames('U_Idle', 4)
        self.animations['walk_up'] = import_frames('U_Walk', 6)

        # LEFT
        self.animations['idle_left'] = import_frames('S_Idle', 4)
        self.animations['walk_left'] = import_frames('S_Walk', 6)

        # RIGHT
        self.animations['idle_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['idle_left']
        ]
        self.animations['walk_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['walk_left']
        ]

    def get_status(self):
        if self.direction.magnitude() != 0:
            if abs(self.direction.x) > abs(self.direction.y):
                if self.direction.x > 0:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
            else:
                if self.direction.y > 0:
                    self.facing = 'down'
                else:
                    self.facing = 'up'

        if self.direction.magnitude() == 0:
            self.status = f'idle_{self.facing}'
        else:
            self.status = f'walk_{self.facing}'

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

        if not current_animation:
            return

        self.frame_index += self.animation_speed * dt
        if self.frame_index >= len(current_animation):
            self.frame_index = 0

        self.image = current_animation[int(self.frame_index)]

    def update(self, dt):
        self.get_input()
        self.get_status()
        self.move(dt)
        self.animate(dt)


class Elf(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.facing = 'down'
        self.load_assets()

        self.status = 'idle_down'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

    def load_assets(self):
        path = "assets/elf/"

        self.animations = {
            'idle_down': [], 'walk_down': [],
            'idle_up': [], 'walk_up': [],
            'idle_left': [], 'walk_left': [],
            'idle_right': [], 'walk_right': []
        }

        def import_frames(name, frame_count):
            img_path = f"{path}{name}.png"
            try:
                sheet = pygame.image.load(img_path).convert_alpha()
            except FileNotFoundError:
                print(f"{img_path} not found.")
                return []  # crash safty

            frames = []
            width = sheet.get_width() // frame_count
            height = sheet.get_height()

            for i in range(frame_count):
                rect = pygame.Rect(i * width, 0, width, height)
                surf = sheet.subsurface(rect)
                scaled = pygame.transform.scale(surf, (width * 5, height * 5))
                frames.append(scaled)
            return frames

        # DOWN
        self.animations['idle_down'] = import_frames('D_Idle', 4)
        self.animations['walk_down'] = import_frames('D_Walk', 6)

        # UP
        self.animations['idle_up'] = import_frames('U_Idle', 4)
        self.animations['walk_up'] = import_frames('U_Walk', 6)

        # LEFT
        self.animations['idle_left'] = import_frames('S_Idle', 4)
        self.animations['walk_left'] = import_frames('S_Walk', 6)

        # RIGHT
        self.animations['idle_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['idle_left']
        ]
        self.animations['walk_right'] = [
            pygame.transform.flip(img, True, False) for img in self.animations['walk_left']
        ]

    def get_status(self):
        if self.direction.magnitude() != 0:
            if abs(self.direction.x) > abs(self.direction.y):
                if self.direction.x > 0:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
            else:
                if self.direction.y > 0:
                    self.facing = 'down'
                else:
                    self.facing = 'up'

        if self.direction.magnitude() == 0:
            self.status = f'idle_{self.facing}'
        else:
            self.status = f'walk_{self.facing}'

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

        if not current_animation:
            return

        self.frame_index += self.animation_speed * dt
        if self.frame_index >= len(current_animation):
            self.frame_index = 0

        self.image = current_animation[int(self.frame_index)]

    def update(self, dt):
        self.get_input()
        self.get_status()
        self.move(dt)
        self.animate(dt)
