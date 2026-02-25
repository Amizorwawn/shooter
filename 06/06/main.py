from kivymd.app import MDApp
from kivymd.uix.widget import MDWidget
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy import platform
from kivy.uix.image import Image
from random import randint
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Keyboard
from kivy.properties import NumericProperty
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.fitimage import FitImage

# Константы
FPS = 60
BULLET_SPEED = dp(10)
SHIP_SPEED = dp(5)
DIR_UP = 1
DIR_DOWN = -1
SPAWN_ENEMY_TIME = 2
HP_DEF = 5
HP_en = 1
FIRE_RATE_MIN = 0.1
FIRE_RATE_MEDIUM = 2


class Shot(MDWidget):
    def __init__(self, direction, owner, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.owner = owner


class Heal(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = 'assets/images/heal.png'  # Убедитесь, что файл существует
        self.size_hint = (None, None)
        self.size = (dp(40), dp(40))

    def update(self, dt):
        self.y -= dp(2)


class Ship(Image):
    hp = NumericProperty()
    max_hp = NumericProperty()

    def __init__(self, direction=DIR_UP, hp=HP_DEF, fire_rate=FIRE_RATE_MEDIUM, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.hp = self.max_hp = hp
        self.fire_rate = fire_rate
        self._last_shot = self.fire_rate
        self.anim_delay = 0.05
        self._lastAnim = self.anim_delay
        self._currentAnim = 0

    def on_kv_post(self, base_widget):
        self.images = [self.source]
        return super().on_kv_post(base_widget)

    def moveLeft(self):
        self.pos[0] -= SHIP_SPEED

    def moveRight(self):
        self.pos[0] += SHIP_SPEED

    def shot(self):
        shot = Shot(self.direction, owner=self)
        shot.center_x = self.center_x
        shot.y = self.top if self.direction == DIR_UP else self.y - shot.height
        app = MDApp.get_running_app()
        game_screen = app.root.get_screen('game')
        game_screen.bullets.append(shot)
        game_screen.ids.front.add_widget(shot)
        self._last_shot = 0

    def update(self, dt):
        self._last_shot += dt
        self.animation(dt)

    def animation(self, dt):
        if hasattr(self, 'images') and len(self.images) > 1:
            if self._lastAnim >= self.anim_delay:
                self.source = self.images[self._currentAnim]
                self._currentAnim = (self._currentAnim + 1) % len(self.images)
                self._lastAnim = 0
            self._lastAnim += dt


class PlayerShip(Ship):
    def __init__(self, **kwargs):
        super().__init__(direction=DIR_UP, fire_rate=FIRE_RATE_MIN, **kwargs)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        # Если файлов нет, закомментируйте эту строку
        self.images.extend(['assets/images/rocket_2.png', 'assets/images/rocket_3.png', 'assets/images/rocket_4.png'])

    def update(self, dt, keys):
        super().update(dt)
        for key in keys:
            if keys.get(key):
                if key == 'left' and self.center_x > 0:
                    self.moveLeft()
                if key == 'right' and self.center_x < Window.width:
                    self.moveRight()
                if key == 'shot':
                    if self._last_shot >= self.fire_rate:
                        self.shot()
                    keys[key] = False


class EnemyShip(Ship):
    def __init__(self, **kwargs):
        super().__init__(direction=DIR_DOWN, hp=HP_en, **kwargs)

    def update(self, dt):
        super().update(dt)
        self.y -= dp(3)
        if self._last_shot >= self.fire_rate:
            self.shot()


class MoveBackground(MDFloatLayout):
    def __init__(self, source, speed=dp(1), scale=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speed = speed
        self.add_widget(FitImage(source=source, size_hint_y=scale))
        self.add_widget(FitImage(source=source, size_hint_y=scale, pos=(0, Window.size[1] * scale)))

    def move(self):
        for img in self.children:
            img.pos[1] -= self.speed
            if img.top <= 0:
                img.pos[1] = img.size[1]


class GameScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eventkeys = {}
        self.ship = None
        self.enemyShips = []
        self.bullets = []
        self.heals = []
        self.pauseMenu = None
        self.spawn_delay = SPAWN_ENEMY_TIME
        self.time_last_spawn = 0

    def on_kv_post(self, base_widget):
        self.backBack = MoveBackground(source='assets/images/cosmos.jpg', speed=0.2)
        self.backFront = MoveBackground(source='assets/images/planets.png', speed=1, scale=3)
        self.ids.back.add_widget(self.backBack)
        self.ids.back.add_widget(self.backFront)
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_key_up=self._on_key_up)

    def on_enter(self, *args):
        app = MDApp.get_running_app()
        app.score = 0
        app.last_checkpoint = 0
        self.ship = self.ids.ship
        self.ship.hp = self.ship.max_hp
        self.enemyShips = []
        self.bullets = []
        self.heals = []
        self.ids.front.clear_widgets()
        self.ids.front.add_widget(self.ship)
        self.updateEvent = Clock.schedule_interval(self.update, 1 / FPS)

    def quit_to_menu(self):
        Clock.unschedule(self.update)
        self.manager.current = 'main'

    def spawn_enemy(self):
        enemy = EnemyShip()
        enemy.x = randint(0, max(1, int(Window.width - enemy.width)))
        enemy.y = Window.height
        self.enemyShips.append(enemy)
        self.ids.front.add_widget(enemy)

    def update(self, dt):
        app = MDApp.get_running_app()
        self.ship.update(dt, self.eventkeys)

        self.time_last_spawn += dt
        if self.time_last_spawn >= self.spawn_delay:
            self.spawn_enemy()
            self.time_last_spawn = 0
        for enemy in self.enemyShips[:]:
            enemy.update(dt)
            if enemy.top < 0:
                self.remove_enemy(enemy)
                self.ship.hp -= 1
                if self.ship.hp <= 0: self.game_over()
            elif enemy.collide_widget(self.ship):
                self.game_over()
        for h in self.heals[:]:
            h.update(dt)
            if h.collide_widget(self.ship):
                if self.ship.hp < self.ship.max_hp:
                    self.ship.hp += 1
                self.remove_heal(h)
            elif h.top < 0:
                self.remove_heal(h)

        self.manage_bullets()
        self.backBack.move()
        self.backFront.move()

    def manage_bullets(self):
        for bullet in self.bullets[:]:
            bullet.y += BULLET_SPEED * bullet.direction
            self.check_collisions(bullet)
            if bullet.top < 0 or bullet.y > Window.height:
                self.remove_bullet(bullet)

    def check_collisions(self, bullet):
        app = MDApp.get_running_app()
        if bullet.owner == self.ship:
            for enemy in self.enemyShips[:]:
                if bullet.collide_widget(enemy):
                    enemy.hp -= 1
                    if enemy.hp <= 0:
                        if randint(1, 100) <= 5:
                            new_heal = Heal()
                            new_heal.center = enemy.center
                            self.heals.append(new_heal)
                            self.ids.front.add_widget(new_heal)

                        self.remove_enemy(enemy)
                        app.score += 1

                        # Чекпоинт в бесконечном режиме
                        if app.target_score == 0:
                            current_cp = int(app.score // app.checkpoint_step)
                            if current_cp > app.last_checkpoint:
                                app.last_checkpoint = current_cp
                                self.ship.hp += 1

                        # Победа в обычном режиме
                        if app.target_score > 0 and app.score >= app.target_score:
                            self.victory()
                    self.remove_bullet(bullet)
                    break
        else:
            if bullet.collide_widget(self.ship):
                self.ship.hp -= 1
                if self.ship.hp <= 0: self.game_over()
                self.remove_bullet(bullet)

    def remove_enemy(self, enemy):
        if enemy in self.enemyShips:
            self.enemyShips.remove(enemy)
            self.ids.front.remove_widget(enemy)

    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.ids.front.remove_widget(bullet)

    def remove_heal(self, heal):
        if heal in self.heals:
            self.heals.remove(heal)
            self.ids.front.remove_widget(heal)

    def victory(self):
        Clock.unschedule(self.update)
        self.manager.current = 'victory'

    def game_over(self):
        Clock.unschedule(self.update)
        self.manager.current = 'game_over'

    def pressKey(self, key):
        self.eventkeys[key] = True

    def releaseKey(self, key):
        self.eventkeys[key] = False

    def show_menu(self):
        Clock.unschedule(self.update)
        if not self.pauseMenu:
            self.pauseMenu = MDDialog(
                title="Пауза",
                text="Продовжити гру?",
                on_dismiss=self.resumeGame,
                buttons=[MDFlatButton(text="ПРОДОВЖИТИ", on_press=lambda x: self.pauseMenu.dismiss())],
            )
        self.pauseMenu.open()

    def resumeGame(self, *args):
        self.updateEvent = Clock.schedule_interval(self.update, 1 / FPS)

    def _on_key_down(self, window, keycode, *args, **kwargs):
        key = Keyboard.keycode_to_string(window, keycode)
        if key == 'spacebar': key = 'shot'
        self.eventkeys[key] = True

    def _on_key_up(self, window, keycode, *args, **kwargs):
        key = Keyboard.keycode_to_string(window, keycode)
        if key == 'spacebar': key = 'shot'
        self.eventkeys[key] = False


class MainScreen(MDScreen): pass


class SettingsScreen(MDScreen): pass


class GameOverScreen(MDScreen): pass


class VictoryScreen(MDScreen): pass


class ShooterApp(MDApp):
    score = NumericProperty(0)
    target_score = NumericProperty(10)
    checkpoint_step = NumericProperty(20)
    last_checkpoint = 0

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"
        self.sm = MDScreenManager()
        self.sm.add_widget(MainScreen(name='main'))
        self.sm.add_widget(GameScreen(name='game'))
        self.sm.add_widget(GameOverScreen(name='game_over'))
        self.sm.add_widget(VictoryScreen(name='victory'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        return self.sm


if __name__ == "__main__":
    if platform != 'android': Window.size = (450, 800)
    ShooterApp().run()