"""
にゃんこ大戦争風ゲームの共通基本機能（ベース部分）

右側の自陣から味方ユニット（ネコ）を出撃させ，左側の敵陣を攻略するゲーム．
お金は時間とともに増え，お金とクールダウンの許す範囲でユニットを出撃できる．
ユニットは敵に当たると立ち止まって攻撃し，敵陣のHPを0にすれば勝利．

操作：数字キー1～3，または画面下のボタンのクリックでユニットを出撃
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
#--------------------------------------------------------------------------------追加機能3
BOSS_TIME = 1000  # ボスが登場するまでの時間（50FPS × 20秒 = 1000フレーム）
#--------------------------------------------------------------------------------追加機能3
BASE_HP = 1000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

#------------------------------------------------------------------難易度（ステージ）の設定（追加機能3）
STAGE_SPECS = [
    {"name": "ノーマル", "rate": 1.0, "color": (100, 200, 100)},
    {"name": "ハード", "rate": 1.2, "color": (220, 80, 80)},
]
#------------------------------------------------------------------

# 味方ユニットの性能（追加機能として種類を増やしやすいように辞書で管理）
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

#--------------------------------------------------------- ボスユニットの性能（追加機能3）ボスの追加
BOSS_SPEC = {
    "name": "ボス", "hp": 1500, "atk": 40, "speed": 0.8,
    "range": 40, "interval": 80,
    "color": (150, 75, 0), "size": (90, 120)
}
#----------------------------------------------------------

def get_font(size: int) -> pg.font.Font:
    """
    日本語を表示できるフォントを探して返す
    引数 size：フォントサイズ
    戻り値：Fontオブジェクト（見つからない場合は標準フォント）
    """
    name = pg.font.match_font(
        "meiryo,yugothic,msgothic,notosanscjkjp,hiraginosans,takaopgothic"
    )
    return pg.font.Font(name, size)


def draw_hp_bar(screen: pg.Surface, rct: pg.Rect, hp: int, max_hp: int) -> None:
    """
    対象の頭上にHPバーを描画する
    引数 screen：画面Surface
    引数 rct：対象のRect
    引数 hp：現在のHP
    引数 max_hp：最大HP
    """
    ratio = max(0, hp) / max_hp
    bar = pg.Rect(rct.left, rct.top - 10, rct.width, 6)
    pg.draw.rect(screen, (80, 80, 80), bar)
    pg.draw.rect(screen, (0, 200, 0), (bar.left, bar.top, int(bar.width * ratio), bar.height))


class Base:
    """
    自陣・敵陣（城）に関するクラス
    """
    def __init__(self, is_cat: bool) -> None:
        """
        引数 is_cat：Trueなら自陣（右側），Falseなら敵陣（左側）
        """
        self.hp = BASE_HP
        self.max_hp = BASE_HP
        self.image = pg.Surface((80, 200))
        self.image.fill((100, 150, 255) if is_cat else (255, 120, 120))
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 3)
        self.rect = self.image.get_rect()
        self.rect.bottom = GROUND_Y
        self.rect.centerx = WIDTH - 80 if is_cat else 80

    def draw(self, screen: pg.Surface) -> None:
        """
        城とHPバーを描画する
        引数 screen：画面Surface
        """
        screen.blit(self.image, self.rect)
        draw_hp_bar(screen, self.rect, self.hp, self.max_hp)


class Unit(pg.sprite.Sprite):
    """
    味方・敵のユニットに関するクラス
    """
    def __init__(self, spec: dict, is_cat: bool, x: int, rate: float = 1.0) -> None:
        """
        引数 spec：ユニットの性能を表す辞書
        引数 is_cat：Trueなら味方（左へ進む），Falseなら敵（右へ進む）
        引数 x：出現位置のx座標（味方は右端，敵は左端をこの座標に合わせる）
        引数 rate：敵ユニットのステータス倍率（ハード時 1.2）
        """
        super().__init__()
        self.spec = spec.copy()
        if not is_cat:  # 敵の場合はステータス（HP・攻撃力）を強化
            self.spec["hp"] = int(spec["hp"] * rate)
            self.spec["atk"] = int(spec["atk"] * rate)

        self.hp = self.spec["hp"]
        self.dir = -1 if is_cat else +1
        self.atk_timer = self.spec["interval"]  # 最初の1発はすぐ撃てるようにする
        self.image = pg.Surface(self.spec["size"])
        self.image.fill(self.spec["color"])
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)
        self.rect = self.image.get_rect()
        self.rect.bottom = GROUND_Y
        if is_cat:
            self.rect.right = x
        else:
            self.rect.left = x
        self.x = float(self.rect.centerx)  # 小数の速度を扱うため，x座標は別に保持する

    def can_reach(self, rct: pg.Rect) -> bool:
        """
        対象のRectが攻撃射程内にあるかを判定する
        引数 rct：敵ユニットまたは敵陣のRect
        戻り値：射程内ならTrue
        """
        if self.dir < 0:
            return rct.right >= self.rect.left - self.spec["range"]
        return rct.left <= self.rect.right + self.spec["range"]

    def find_target(self, opponents: pg.sprite.Group, base: Base) -> "Unit | Base | None":
        """
        攻撃対象を探す（射程内のユニットのうち最も近いもの，いなければ敵城）
        引数 opponents：相手側ユニットのグループ
        引数 base：相手側の城
        戻り値：攻撃対象（いなければNone）
        """
        cands = [o for o in opponents if self.can_reach(o.rect)]
        if cands:
            return min(cands, key=lambda o: abs(o.rect.centerx - self.rect.centerx))
        if self.can_reach(base.rect):
            return base
        return None

    def update(self, opponents: pg.sprite.Group, base: Base) -> None:
        """
        HP判定，攻撃，移動を行う
        引数 opponents：相手側ユニットのグループ
        引数 base：相手側の城
        """
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


class Wallet:
    """
    お金（所持金）に関するクラス
    """
    def __init__(self) -> None:
        self.money = 100.0
        self.max_money = 1000
        self.income = 0.5  # 1フレームあたりの増加量

    def update(self) -> None:
        """
        お金を時間経過で増やす（上限あり）
        """
        self.money = min(self.max_money, self.money + self.income)

    def pay(self, cost: int) -> bool:
        """
        所持金が足りれば支払う
        引数 cost：支払う金額
        戻り値：支払えたらTrue，足りなければFalse
        """
        if self.money < cost:
            return False
        self.money -= cost
        return True


def make_buttons() -> list[pg.Rect]:
    """
    出撃ボタンのRectのリストを作る
    戻り値：味方ユニットの種類ごとのボタンRect
    """
    return [pg.Rect(20 + i * 170, 540, 160, 90) for i in range(len(CAT_SPECS))]


def try_spawn(idx: int, wallet: Wallet, cooldowns: list[int],
              cats: pg.sprite.Group, cat_base: Base) -> None:
    """
    お金とクールダウンの条件を満たせば，味方ユニットを出撃させる
    引数 idx：CAT_SPECSの番号
    引数 wallet：所持金
    引数 cooldowns：ユニットごとの残りクールダウン（フレーム数）
    引数 cats：味方ユニットのグループ
    引数 cat_base：自陣
    """
    spec = CAT_SPECS[idx]
    if cooldowns[idx] > 0 or not wallet.pay(spec["cost"]):
        return
    cats.add(Unit(spec, True, cat_base.rect.left))
    cooldowns[idx] = spec["cooldown"]


def draw_ui(screen: pg.Surface, font: pg.font.Font, wallet: Wallet,
            cooldowns: list[int], buttons: list[pg.Rect]) -> None:
    """
    所持金表示と出撃ボタンを描画する
    引数 screen：画面Surface
    引数 font：表示用フォント
    引数 wallet：所持金
    引数 cooldowns：ユニットごとの残りクールダウン
    引数 buttons：出撃ボタンのRectリスト
    """
    for i, (spec, btn) in enumerate(zip(CAT_SPECS, buttons)):
        usable = cooldowns[i] == 0 and wallet.money >= spec["cost"]
        pg.draw.rect(screen, (255, 230, 120) if usable else (150, 150, 150), btn)
        if cooldowns[i] > 0:  # クールダウン中は残り時間を暗いゲージで示す
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
    """
    背景（空と地面）を描画する
    引数 screen：画面Surface
    """
    screen.fill((135, 206, 235))
    pg.draw.rect(screen, (150, 110, 70), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pg.draw.line(screen, (0, 0, 0), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)


def show_result(screen: pg.Surface, font: pg.font.Font, message: str) -> None:
    """
    勝敗の結果を3秒間表示する
    引数 screen：画面Surface
    引数 font：表示用フォント
    引数 message：表示する文字列
    """
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    screen.blit(overlay, (0, 0))
    text = font.render(message, True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pg.display.update()
    time.sleep(3)

#------------------------------------------------------------------------------------------------------------------------#追加機能3
def select_stage_screen(screen: pg.Surface, font: pg.font.Font, title_font: pg.font.Font) -> dict | None:    
    """
    ステージ（難易度）選択画面
    戻り値：選択した難易度の設定辞書
    """
    clock = pg.time.Clock()
    buttons = [
        pg.Rect(WIDTH // 2 - 150, 250 + i * 120, 300, 80)
        for i in range(len(STAGE_SPECS))
    ]

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return None
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(event.pos):
                        return STAGE_SPECS[i]       #追加機能3

        screen.fill((240, 230, 200))
        title = title_font.render("ステージ選択", True, (0, 0, 0))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

        for spec, btn in zip(STAGE_SPECS, buttons):
            pg.draw.rect(screen, spec["color"], btn, border_radius=10)
            pg.draw.rect(screen, (0, 0, 0), btn, 3, border_radius=10)
            text = font.render(spec["name"], True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=btn.center))

        pg.display.update()
        clock.tick(FPS)
#------------------------------------------------------------------------------------- #追加機能3

def main() -> None:
    pg.display.set_caption("ネコ大戦争（仮）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    font = get_font(26)
    big_font = get_font(90)
    title_font = get_font(50)
    clock = pg.time.Clock()
#----------------------------------------------------------------追加機能3　ゲーム開始時に難易度の選択
    stage_spec = select_stage_screen(screen, font, title_font)
    if stage_spec is None:
        return
#----------------------------------------------------------------追加機能3
#--------------------------------------追加機能3 難易度(rate)の倍率を取得
    enemy_rate = stage_spec["rate"]
#--------------------------------------追加機能3
    cat_base, enemy_base = Base(True), Base(False)
    cats, enemies = pg.sprite.Group(), pg.sprite.Group()
    wallet = Wallet()
    cooldowns = [0] * len(CAT_SPECS)
    buttons = make_buttons()
    tmr = 0
    #------------------------------------------------------------------
    boss_spawned = False  # ボスが出現済みか管理するフラグ（追加機能3）
    #-------------------------------------------------------------------
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and pg.K_1 <= event.key < pg.K_1 + len(CAT_SPECS):
                try_spawn(event.key - pg.K_1, wallet, cooldowns, cats, cat_base)
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(event.pos):
                        try_spawn(i, wallet, cooldowns, cats, cat_base)

        wallet.update()
        for i in range(len(cooldowns)):
            cooldowns[i] = max(0, cooldowns[i] - 1)

        #-------------------------------------------------------------------------- 一定時間経過後にボスが登場する処理（追加機能3）
        if not boss_spawned and tmr >= BOSS_TIME:
            enemies.add(Unit(BOSS_SPEC, False, enemy_base.rect.right, enemy_rate))
            boss_spawned = True
        #---------------------------------------------------------------------------
        # 通常敵の出現（倍率適用）
        if tmr % ENEMY_INTERVAL == ENEMY_INTERVAL - 1:
            spec = random.choices(ENEMY_SPECS, weights=[3, 1])[0]
            enemies.add(Unit(spec, False, enemy_base.rect.right, enemy_rate))

        cats.update(enemies, enemy_base)
        enemies.update(cats, cat_base)

        draw_field(screen)
        enemy_base.draw(screen)
        cat_base.draw(screen)
        cats.draw(screen)
        enemies.draw(screen)
        for unit in list(cats) + list(enemies):
            draw_hp_bar(screen, unit.rect, unit.hp, unit.spec["hp"])
        draw_ui(screen, font, wallet, cooldowns, buttons)

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