"""
にゃんこ大戦争風ゲーム（ベース＋コインキャッチ＋にゃんこ砲）

右側の自陣から味方ユニット（ネコ）を出撃させ，左側の敵陣を攻略するゲーム．
お金は時間とともに増え，お金とクールダウンの許す範囲でユニットを出撃できる．
ユニットは敵に当たると立ち止まって攻撃し，敵陣のHPを0にすれば勝利．

操作：数字キー1～3，または画面下のボタンのクリックでユニットを出撃
   空から落ちてくるコインをクリックでキャッチするとお金が増加
   自陣上の「準備OK！」をクリックするとにゃんこ砲発射！
"""
import os
import random
import sys
import time

import pygame as pg


WIDTH, HEIGHT = 1100, 650
GROUND_Y = 500  # 地面の高さ（ユニットの足元のy座標）
FPS = 50
ENEMY_INTERVAL = 150  # 敵が出現する間隔（フレーム数）
COIN_INTERVAL = 180   # コインが出現する間隔（フレーム数）
BASE_HP = 1000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 味方ユニットの性能
CAT_SPECS = [
    {"name": "ネコ", "cost": 50, "hp": 100, "atk": 10, "speed": 2.0,
     "range": 20, "interval": 40, "cooldown": 100,
     "color": (255, 220, 160), "size": (40, 50)},
    {"name": "タンク", "cost": 100, "hp": 500, "atk": 6, "speed": 1.2,
     "range": 20, "interval": 50, "cooldown": 200,
     "color": (200, 200, 255), "size": (50, 70)},
    {"name": "キック", "cost": 150, "hp": 120, "atk": 35, "speed": 1.8,
     "range": 60, "interval": 70, "cooldown": 250,
     "color": (255, 150, 150), "size": (40, 60)},
]

# 敵ユニットの性能
ENEMY_SPECS = [
    {"name": "ワンコ", "hp": 120, "atk": 8, "speed": 1.5,
     "range": 20, "interval": 45,
     "color": (240, 240, 240), "size": (40, 40)},
    {"name": "ブタ", "hp": 500, "atk": 20, "speed": 1.0,
     "range": 20, "interval": 60,
     "color": (255, 170, 200), "size": (60, 80)},
]


def get_font(size: int) -> pg.font.Font:
    name = pg.font.match_font(
        "meiryo,yugothic,msgothic,notosanscjkjp,hiraginosans,takaopgothic"
    )
    return pg.font.Font(name, size)

def draw_hp_bar(screen: pg.Surface, rct: pg.Rect, hp: int, max_hp: int) -> None:
    ratio = max(0, hp) / max_hp
    bar = pg.Rect(rct.left, rct.top - 10, rct.width, 6)
    pg.draw.rect(screen, (80, 80, 80), bar)
    pg.draw.rect(screen, (0, 0, 0), bar, 1)
    pg.draw.rect(screen, (0, 200, 0), (bar.left, bar.top, int(bar.width * ratio), bar.height))


class Base:
    def __init__(self, is_cat: bool) -> None:
        self.hp = BASE_HP
        self.max_hp = BASE_HP
        self.image = pg.Surface((80, 200))
        self.image.fill((100, 150, 255) if is_cat else (255, 120, 120))
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 3)
        self.rect = self.image.get_rect()
        self.rect.bottom = GROUND_Y
        self.rect.centerx = WIDTH - 80 if is_cat else 80

    def draw(self, screen: pg.Surface) -> None:
        screen.blit(self.image, self.rect)
        draw_hp_bar(screen, self.rect, self.hp, self.max_hp)


class Unit(pg.sprite.Sprite):
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__()
        self.spec = spec
        self.hp = spec["hp"]
        self.dir = -1 if is_cat else +1
        self.atk_timer = spec["interval"]
        self.image = pg.Surface(spec["size"])
        self.image.fill(spec["color"])
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)
        self.rect = self.image.get_rect()
        self.rect.bottom = GROUND_Y
        if is_cat:
            self.rect.right = x
        else:
            self.rect.left = x
        self.x = float(self.rect.centerx)

    def can_reach(self, rct: pg.Rect) -> bool:
        if self.dir < 0:
            return rct.right >= self.rect.left - self.spec["range"]
        return rct.left <= self.rect.right + self.spec["range"]

    def find_target(self, opponents: pg.sprite.Group, base: Base) -> "Unit | Base | None":
        cands = [o for o in opponents if self.can_reach(o.rect)]
        if cands:
            return min(cands, key=lambda o: abs(o.rect.centerx - self.rect.centerx))
        if self.can_reach(base.rect):
            return base
        return None

    def update(self, opponents: pg.sprite.Group, base: Base) -> None:
        if self.hp <= 0:
            self.kill()
            return
        target = self.find_target(opponents, base)
        if target is None:
            self.x += self.dir * self.spec["speed"]
            self.rect.centerx = int(self.x)
            return
        self.atk_timer += 1
        if self.atk_timer >= self.spec["interval"]:
            target.hp -= self.spec["atk"]
            self.atk_timer = 0


class Coin(pg.sprite.Sprite):
    def __init__(self, reward: int = 50) -> None:
        super().__init__()
        self.reward = reward
        self.radius = 16
        self.image = pg.Surface((self.radius * 2, self.radius * 2), pg.SRCALPHA)
        pg.draw.circle(self.image, (255, 215, 0), (self.radius, self.radius), self.radius)
        pg.draw.circle(self.image, (218, 165, 32), (self.radius, self.radius), self.radius, 2)
        
        self.rect = self.image.get_rect()
        self.rect.centerx = random.randint(50, WIDTH - 50)
        self.rect.bottom = 0
        self.speed = random.uniform(1.5, 3.0)

    def update(self) -> None:
        self.rect.y += self.speed
        if self.rect.top > GROUND_Y:
            self.kill()


class CatCannon:
    """
    にゃんこ砲クラス
    """
    def __init__(self, cat_base: Base) -> None:
        self.cat_base = cat_base
        self.max_charge = 1000  # チャージ完了までのフレーム数（10秒）
        self.charge = 0        # 現在のチャージ量
        self.damage = 200      # 敵全体へのダメージ
        self.beam_timer = 0    # ビームの描画用タイマー

        # 自陣の城の上に表示する「準備OK！」UIのRect
        self.btn_rect = pg.Rect(0, 0, 110, 40)
        self.btn_rect.centerx = cat_base.rect.centerx
        self.btn_rect.bottom = cat_base.rect.top - 15

    def is_ready(self) -> bool:
        """チャージが満タンかどうか"""
        return self.charge >= self.max_charge

    def update(self) -> None:
        """チャージ進行およびビームタイマー更新"""
        if not self.is_ready():
            self.charge += 1
        if self.beam_timer > 0:
            self.beam_timer -= 1

    def try_fire(self, pos: tuple[int, int], enemies: pg.sprite.Group) -> bool:
        """
        「準備OK！」ボタンが押されたらビームを発射し、画面内の敵全体にダメージ
        """
        if self.is_ready() and self.btn_rect.collidepoint(pos):
            self.charge = 0
            self.beam_timer = 15  # ビーム表示フレーム数
            # 全敵ユニットへダメージを与える
            for enemy in enemies:
                enemy.hp -= self.damage
            return True
        return False

    def draw(self, screen: pg.Surface, font: pg.font.Font) -> None:
        """UI（準備OKボタン / ゲージ）とビームの描画"""
        # --- ビームエフェクト描画 ---
        if self.beam_timer > 0:
            beam_rect = pg.Rect(0, GROUND_Y - 80, self.cat_base.rect.centerx, 80)
            beam_surface = pg.Surface((beam_rect.width, beam_rect.height), pg.SRCALPHA)
            # (R, G, B, 透明度A)
            beam_surface.fill((200, 100, 255, 180))  # 紫色の外光
            pg.draw.rect(beam_surface, (230, 180, 255, 230), (0, 15, beam_rect.width, 50))  # 明るい紫色の芯
            screen.blit(beam_surface, beam_rect)

        # --- UI描画（城の上） ---
        if self.is_ready():
            # 準備OKボタン（点滅っぽく黄色で強調）
            pg.draw.rect(screen, (255, 215, 0), self.btn_rect, border_radius=8)
            pg.draw.rect(screen, (255, 255, 255), self.btn_rect, 3, border_radius=8)
            text = font.render("準備OK!", True, (0, 0, 0))
            screen.blit(text, text.get_rect(center=self.btn_rect.center))
        else:
            # チャージ中ゲージ
            gauge_bg = pg.Rect(self.btn_rect.left, self.btn_rect.bottom - 12, self.btn_rect.width, 12)
            ratio = self.charge / self.max_charge
            gauge_fg = pg.Rect(gauge_bg.left, gauge_bg.top, int(gauge_bg.width * ratio), gauge_bg.height)
            
            pg.draw.rect(screen, (60, 60, 60), gauge_bg, border_radius=4)
            pg.draw.rect(screen, (100, 200, 255), gauge_fg, border_radius=4)
            pg.draw.rect(screen, (0, 0, 0), gauge_bg, 1, border_radius=4)


class Wallet:
    def __init__(self) -> None:
        self.money = 100.0
        self.max_money = 1000
        self.income = 0.5

    def update(self) -> None:
        self.money = min(self.max_money, self.money + self.income)

    def add_money(self, amount: int) -> None:
        self.money = min(self.max_money, self.money + amount)

    def pay(self, cost: int) -> bool:
        if self.money < cost:
            return False
        self.money -= cost
        return True


def make_buttons() -> list[pg.Rect]:
    return [pg.Rect(20 + i * 170, 540, 160, 90) for i in range(len(CAT_SPECS))]

def try_spawn(idx: int, wallet: Wallet, cooldowns: list[int],
              cats: pg.sprite.Group, cat_base: Base) -> None:
    spec = CAT_SPECS[idx]
    if cooldowns[idx] > 0 or not wallet.pay(spec["cost"]):
        return
    cats.add(Unit(spec, True, cat_base.rect.left))
    cooldowns[idx] = spec["cooldown"]

def draw_ui(screen: pg.Surface, font: pg.font.Font, wallet: Wallet,
            cooldowns: list[int], buttons: list[pg.Rect]) -> None:
    for i, (spec, btn) in enumerate(zip(CAT_SPECS, buttons)):
        usable = cooldowns[i] == 0 and wallet.money >= spec["cost"]
        pg.draw.rect(screen, (255, 230, 120) if usable else (150, 150, 150), btn)
        if cooldowns[i] > 0:
            h = int(btn.height * cooldowns[i] / spec["cooldown"])
            pg.draw.rect(screen, (90, 90, 90), (btn.left, btn.top, btn.width, h))
        pg.draw.rect(screen, (0, 0, 0), btn, 3)
        name = font.render(f"{i + 1}:{spec['name']}", True, (0, 0, 0))
        cost = font.render(f"{spec['cost']}円", True, (0, 0, 0))
        screen.blit(name, (btn.left + 10, btn.top + 10))
        screen.blit(cost, (btn.left + 10, btn.top + 50))
    money = font.render(f"お金 {int(wallet.money)} / {wallet.max_money}円", True, (0, 0, 0))
    screen.blit(money, (WIDTH - money.get_width() - 20, 20))

def draw_field(screen: pg.Surface) -> None:
    screen.fill((135, 206, 235))
    pg.draw.rect(screen, (150, 110, 70), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pg.draw.line(screen, (0, 0, 0), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)

def show_result(screen: pg.Surface, font: pg.font.Font, message: str) -> None:
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    screen.blit(overlay, (0, 0))
    text = font.render(message, True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pg.display.update()
    time.sleep(3)

def main() -> None:
    pg.display.set_caption("ネコ大戦争（仮）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    font = get_font(26)
    btn_font = get_font(20)
    big_font = get_font(90)
    clock = pg.time.Clock()

    cat_base, enemy_base = Base(True), Base(False)
    cats, enemies = pg.sprite.Group(), pg.sprite.Group()
    coins = pg.sprite.Group()
    cannon = CatCannon(cat_base)  # にゃんこ砲生成
    wallet = Wallet()
    cooldowns = [0] * len(CAT_SPECS)
    buttons = make_buttons()
    tmr = 0

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and pg.K_1 <= event.key < pg.K_1 + len(CAT_SPECS):
                try_spawn(event.key - pg.K_1, wallet, cooldowns, cats, cat_base)

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # 1. にゃんこ砲発射判定
                if cannon.try_fire(event.pos, enemies):
                    continue

                # 2. コインキャッチ判定
                clicked_coin = False
                for coin in list(coins):
                    if coin.rect.collidepoint(event.pos):
                        wallet.add_money(coin.reward)
                        coin.kill()
                        clicked_coin = True
                        break

                # 3. 出撃ボタン判定
                if not clicked_coin:
                    for i, btn in enumerate(buttons):
                        if btn.collidepoint(event.pos):
                            try_spawn(i, wallet, cooldowns, cats, cat_base)

        wallet.update()
        cannon.update()  # にゃんこ砲のチャージ更新

        for i in range(len(cooldowns)):
            cooldowns[i] = max(0, cooldowns[i] - 1)

        # 敵の定期出現
        if tmr % ENEMY_INTERVAL == ENEMY_INTERVAL - 1:
            spec = random.choices(ENEMY_SPECS, weights=[3, 1])[0]
            enemies.add(Unit(spec, False, enemy_base.rect.right))

        # コインの定期出現
        if tmr % COIN_INTERVAL == COIN_INTERVAL - 1:
            coins.add(Coin(reward=50))

        cats.update(enemies, enemy_base)
        enemies.update(cats, cat_base)
        coins.update()

        # 描画処理
        draw_field(screen)
        enemy_base.draw(screen)
        cat_base.draw(screen)
        cats.draw(screen)
        enemies.draw(screen)
        coins.draw(screen)

        for unit in list(cats) + list(enemies):
            draw_hp_bar(screen, unit.rect, unit.hp, unit.spec["hp"])

        draw_ui(screen, font, wallet, cooldowns, buttons)
        cannon.draw(screen, btn_font)  # にゃんこ砲のUIとビームを描画

        if enemy_base.hp <= 0:
            show_result(screen, big_font, "勝利！")
            return
        if cat_base.hp <= 0:
            show_result(screen, big_font, "敗北…")
            return

        pg.display.update()
        tmr += 1
        clock.tick(FPS)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()