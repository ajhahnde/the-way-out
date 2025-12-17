import pygame
from units import Wizard, Penguin, Elf

LEVEL_DATA = [
    {   # Level 1 (Index 0)
        "bg": "assets/background/test_bg_1.png",
        "player_start": (100, 300),
        "portal": (50, 50),
        "enemy": [(400, 300), (600, 400)]
    },
    {   # Level 2 (Index 1)
        "bg": "assets/background/test_bg_2.png",
        "player_start": (50, 50),
        "portal": (50, 50),
        "enemy": [(200, 200), (300, 500), (800, 100)]
    },
    {   # Level 3 (Index 2)
        "bg": "assets/background/level3_bg.png",
        "player_start": (640, 360),
        "portal": [()],
        "enemy": [()]
    }
]


class LevelManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.display_surface = pygame.display.get_surface()
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()

        self.bg_image = None
        self.current_level_index = 0

    def load_level(self, level_index, char_type="c_wiz"):
        self.current_level_index = level_index
        data = LEVEL_DATA[level_index]
        self.all_sprites.empty()
        self.enemies.empty()

        try:
            self.bg_image = pygame.image.load(data["bg"]).convert()
            self.bg_image = pygame.transform.scale(
                self.bg_image, (self.width, self.height))
        except FileNotFoundError:
            print(f"{data['bg']} not found.")
            self.bg_image = pygame.Surface((self.width, self.height))
            self.bg_image.fill((50, 50, 50))

        # create player based on char_type
        start_x, start_y = data["player_start"]

        if char_type == "c_wiz":
            self.player = Wizard(start_x, start_y)
        elif char_type == "c_peng":
            self.player = Penguin(start_x, start_y)
        elif char_type == "c_elf":
            self.player = Elf(start_x, start_y)
        else:
            self.player = Wizard(start_x, start_y)  # Fallback

        self.all_sprites.add(self.player)

        # create enemy
        # for pos in data["enemy"]:
        #     enemy = Enemy(pos[0], pos[1])
        #     self.enemies.add(enemy)
        #     self.all_sprites.add(enemy)

    def update(self, dt):
        self.all_sprites.update(dt)

    def draw(self, screen):
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))

        self.all_sprites.draw(screen)
