import pygame
from settings import FONT


class MainMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.Font(FONT, 60)

        self.buttons = [
            {"text": "Levels", "rect": None, "action": "lvls"},
            {"text": "Characters", "rect": None, "action": "chars"},
            {"text": "Settings", "rect": None, "action": "settings"},
            {"text": "Quit", "rect": None, "action": "quit"}
        ]

        center_x = width // 2
        start_y = height // 2 - 50

        for i, btn in enumerate(self.buttons):
            text_surf = self.font.render(btn["text"], True, (255, 255, 255))
            rect = text_surf.get_rect(center=(center_x, start_y + i * 100))
            btn["rect"] = rect

    def draw(self, screen):
        screen.fill((20, 20, 30))
        mouse_pos = pygame.mouse.get_pos()

        for btn in self.buttons:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            color = (255, 215, 0) if is_hovered else (200, 200, 200)
            text_surf = self.font.render(btn["text"], True, color)
            screen.blit(text_surf, btn["rect"])

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    return btn["action"]
        return None


class SettingsMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.Font(FONT, 60)
        self.sound_on = True
        self.toggle_screen = True
        self.screen_size_index = 0

        self.resolutions = [
            (2560, 1600),
            (1920, 1080),
            (1280, 960)
        ]

        self.update_buttons()

    def update_buttons(self):
        sound_text = f"Sound: {'ON' if self.sound_on else 'OFF'}"
        screen_text = f"{'FULLSCREEN' if self.toggle_screen else 'WINDOW'}"

        w, h = self.resolutions[self.screen_size_index]
        screen_size_t = f"{w}x{h}"

        self.buttons = [
            {"text": sound_text, "rect": None, "action": "toggle_sound"},
            {"text": screen_text, "rect": None, "action": "toggle_fs_w"},
            {"text": screen_size_t, "rect": None, "action": "toggle_screen_size"}
        ]

        center_x = self.width // 2
        start_y = self.height // 2 - 50

        for i, btn in enumerate(self.buttons):
            text_surf = self.font.render(btn["text"], True, (255, 255, 255))
            btn["rect"] = text_surf.get_rect(
                center=(center_x, start_y + i * 100))

    def draw(self, screen):
        screen.fill((40, 30, 50))

        title = self.font.render("Settings", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, 100))
        screen.blit(title, title_rect)

        back_font = pygame.font.Font(FONT, 30)
        back = back_font.render("Esc to Back", True, (255, 255, 255))
        back_rect = back.get_rect(center=(100, 50))
        screen.blit(back, back_rect)

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            color = (255, 215, 0) if is_hovered else (200, 200, 200)
            screen.blit(self.font.render(
                btn["text"], True, color), btn["rect"])

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    if btn["action"] == "toggle_sound":
                        self.sound_on = not self.sound_on
                        self.update_buttons()

                    elif btn["action"] == "toggle_fs_w":
                        self.toggle_screen = not self.toggle_screen
                        pygame.display.toggle_fullscreen()
                        self.update_buttons()

                    elif btn["action"] == "toggle_screen_size":
                        self.screen_size_index = (
                            self.screen_size_index + 1) % len(self.resolutions)
                        new_res = self.resolutions[self.screen_size_index]

                        flags = pygame.FULLSCREEN if self.toggle_screen else 0
                        pygame.display.set_mode(new_res, flags)

                        self.width, self.height = new_res
                        self.update_buttons()

                    return btn["action"]
        return None


class LevelMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.Font(FONT, 60)

        self.buttons = [
            {"text": "Level 1", "rect": None, "action": "level1"},
            {"text": "Level 2", "rect": None, "action": "level2"},
            {"text": "Level 3", "rect": None, "action": "level3"}
        ]

        center_x = width // 2
        start_y = height // 2 - 50

        for i, btn in enumerate(self.buttons):
            text_surf = self.font.render(btn["text"], True, (255, 255, 255))
            rect = text_surf.get_rect(center=(center_x, start_y + i * 100))
            btn["rect"] = rect

    def draw(self, screen):
        screen.fill((20, 20, 30))
        title = self.font.render("Levels", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, 100))
        screen.blit(title, title_rect)

        back_font = pygame.font.Font(FONT, 30)
        back = back_font.render("Esc to Back", True, (255, 255, 255))
        back_rect = back.get_rect(center=(100, 50))
        screen.blit(back, back_rect)

        mouse_pos = pygame.mouse.get_pos()

        for btn in self.buttons:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            color = (255, 215, 0) if is_hovered else (200, 200, 200)
            text_surf = self.font.render(btn["text"], True, color)
            screen.blit(text_surf, btn["rect"])

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    return btn["action"]
        return None


class CharacterMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.Font(FONT, 60)

        self.character = [
            {"text": "Wizard", "rect": None, "action": "c_wiz"},
            {"text": "Penguin", "rect": None, "action": "c_peng"},
            {"text": "Elf", "rect": None, "action": "c_elf"}
        ]

        center_x = width // 2
        start_y = height // 2 - 50

        for i, btn in enumerate(self.character):
            text_surf = self.font.render(btn["text"], True, (255, 255, 255))
            rect = text_surf.get_rect(center=(center_x, start_y + i * 100))
            btn["rect"] = rect

    def draw(self, screen, current_selected):
        screen.fill((20, 20, 30))

        # Titel
        title = self.font.render("Select Character", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, 100))
        screen.blit(title, title_rect)

        back_font = pygame.font.Font(FONT, 30)
        back = back_font.render("Esc to Back", True, (255, 255, 255))
        back_rect = back.get_rect(center=(100, 50))
        screen.blit(back, back_rect)

        mouse_pos = pygame.mouse.get_pos()

        for btn in self.character:
            is_hovered = btn["rect"].collidepoint(mouse_pos)

            if btn["action"] == current_selected:
                color = (0, 255, 0)
            elif is_hovered:
                color = (255, 215, 0)
            else:
                color = (200, 200, 200)

            text_surf = self.font.render(btn["text"], True, color)
            screen.blit(text_surf, btn["rect"])

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.character:
                if btn["rect"].collidepoint(mouse_pos):
                    return btn["action"]
        return None
