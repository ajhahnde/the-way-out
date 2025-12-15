import pygame


class MainMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont("Arial", 60, bold=True)

        self.buttons = [
            {"text": "Start", "rect": None, "action": "game"},
            {"text": "Settings", "rect": None, "action": "settings"},
            {"text": "Beenden", "rect": None, "action": "quit"}
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
            color = (255, 215, 0) if is_hovered else (
                200, 200, 200)

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
        self.font = pygame.font.SysFont("Arial", 60, bold=True)

        self.sound_on = True

        self.update_buttons()

    def update_buttons(self):
        sound_text = f"Sound: {'AN' if self.sound_on else 'AUS'}"

        self.buttons = [
            {"text": sound_text, "rect": None, "action": "toggle_sound"},
            {"text": "Zurück", "rect": None, "action": "back"}
        ]

        center_x = self.width // 2
        start_y = self.height // 2 - 50

        for i, btn in enumerate(self.buttons):
            text_surf = self.font.render(btn["text"], True, (255, 255, 255))
            btn["rect"] = text_surf.get_rect(
                center=(center_x, start_y + i * 100))

    def draw(self, screen):
        screen.fill((40, 30, 50))

        # Titel
        title = self.font.render("Settings", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, 100))
        screen.blit(title, title_rect)

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
                        # später pygame.mixer.music.set_volume() aufrufen

                    return btn["action"]
        return None


# class MenuWhenInGame:
