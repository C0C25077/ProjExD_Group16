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
BASE_HP = 1000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 味方ユニットの性能（追加機能として種類を増やしやすいように辞書で管理）
CAT_SPECS = [
    {"name": "ネコ", "cost": 50, "hp": 100, "atk": 10, "speed": 2.0,
     "range": 20, "interval": 40, "cooldown": 100,
     "color": (255, 220, 160), "size": (40, 50)},
    {"name": "タンク", "cost": 100, "hp": 500, "atk": 6, "speed": 1.2,
     "range": 20, "interval": 50, "cooldown": 200,
     "color": (200, 200, 255), "size": (50, 70)},
     {"name": "アーチャー", "kind": "shooter", "cost": 120, "hp": 80, "atk": 12,
     "speed": 1.6, "range": 220, "interval": 60, "cooldown": 150,
     "color": (150, 255, 150), "size": (35, 55)},
    {"name": "キック", "cost": 150, "hp": 120, "atk": 35, "speed": 1.8,
     "range": 60, "interval": 70, "cooldown": 250,
     "color": (255, 150, 150), "size": (40, 60)},
    {"name": "ボンバー", "kind": "area", "cost": 200, "hp": 150, "atk": 20,
     "area": 80, "speed": 1.5, "range": 40, "interval": 90, "cooldown": 300,
     "color": (255, 120, 0), "size": (45, 55)},
    {"name": "飛行戦艦", "kind": "warship", "cost": 1000, "hp": 600, "atk": 25,
     "area": 150, "knockback": 40, "blast_every": 4, "blast_area": 320,
     "fly": 250, "speed": 1.0, "range": 200, "interval": 80, "cooldown": 600,
     "color": (90, 110, 140), "size": (250, 70)},
    {"name": "ケサラン", "kind": "kesaran", "cost": 300, "hp": 60, "atk": 6,
     "area": 100, "knockback": 60, "stun": 40, "fly": 30, "speed": 1.4,
     "range": 350, "interval": 100, "cooldown": 400,
     "color": (255, 255, 255), "size": (36, 36)},
]

# 敵ユニットの性能
ENEMY_SPECS = [
    {"name": "ワンコ", "hp": 120, "atk": 8, "speed": 1.5,
     "range": 20, "interval": 45,
     "color": (240, 240, 240), "size": (40, 40)},
    {"name": "ブタ", "hp": 500, "atk": 20, "speed": 1.0,
     "range": 20, "interval": 60,
     "color": (255, 170, 200), "size": (60, 80)},
    {"name": "スタン", "kind": "stopper", "hp": 150, "atk": 5, "speed": 1.3,
     "range": 20, "interval": 90, "stun": 60,
     "color": (200, 200, 80), "size": (40, 50)},
]

BOSS_SPEC = {"name": "ボス", "kind": "boss", "hp": 2000, "atk": 30, "speed": 0.8,
             "range": 30, "interval": 70,
             "color": (120, 40, 40), "size": (100, 140)}
BOSS_TIME = 2500  # ボスが出現するフレーム数

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
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        """
        引数 spec：ユニットの性能を表す辞書
        引数 is_cat：Trueなら味方（左へ進む），Falseなら敵（右へ進む）
        引数 x：出現位置のx座標（味方は右端，敵は左端をこの座標に合わせる）
        """
        super().__init__()
        self.spec = spec
        self.hp = spec["hp"]
        self.dir = -1 if is_cat else +1
        self.stun = 0  # 足止めされている残りフレーム数
        self.atk_timer = spec["interval"]  # 最初の1発はすぐ撃てるようにする
        self.image = pg.Surface(spec["size"])
        self.image.fill(spec["color"])
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
        if self.stun > 0:  # 足止め中は移動も攻撃もしない
            self.stun -= 1
            return
        target = self.find_target(opponents, base)
        if target is None:
            self.x += self.dir * self.spec["speed"]
            self.rect.centerx = int(self.x)
            return
        self.atk_timer += 1
        if self.atk_timer >= self.spec["interval"]:
            self.attack(target, opponents)
            self.atk_timer = 0

    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        攻撃処理（通常は対象1体にダメージ）．サブクラスで上書きして攻撃方法を変える
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        target.hp -= self.spec["atk"]

    def draw_effect(self, screen: pg.Surface) -> None:
        """
        ユニットに関する演出を描画する（足止め中は頭上に黄色い印を出す）
        引数 screen：画面Surface
        """
        if self.stun > 0:
            pg.draw.circle(screen, (255, 255, 0), (self.rect.centerx, self.rect.top - 25), 8)


class AreaUnit(Unit):
    """
    範囲攻撃ユニット：攻撃対象の周囲にいる相手も巻き込んでダメージを与える
    """
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__(spec, is_cat, x)
        self.blast_pos = (0, 0)  # 爆発演出の中心座標
        self.blast_timer = 0  # 爆発演出の残りフレーム数

    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        対象と，対象から範囲area以内にいる相手全員にダメージを与える
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        center_x = target.rect.centerx
        target.hp -= self.spec["atk"]
        for opp in opponents:
            if opp is not target and abs(opp.rect.centerx - center_x) <= self.spec["area"]:
                opp.hp -= self.spec["atk"]
        self.blast_pos = (center_x, GROUND_Y - 20)
        self.blast_timer = 10

    def draw_effect(self, screen: pg.Surface) -> None:
        """
        爆発の範囲を示す円を一定時間描画する
        引数 screen：画面Surface
        """
        super().draw_effect(screen)
        if self.blast_timer > 0:
            pg.draw.circle(screen, (255, 140, 0), self.blast_pos, self.spec["area"], 4)
            self.blast_timer -= 1


class ShooterUnit(Unit):
    """
    遠距離攻撃ユニット：長い射程から光線で攻撃する
    """
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__(spec, is_cat, x)
        self.beam = ((0, 0), (0, 0))  # 光線の始点と終点
        self.beam_timer = 0  # 光線演出の残りフレーム数

    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        対象にダメージを与え，光線の演出を開始する
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        target.hp -= self.spec["atk"]
        self.beam = (self.rect.center, target.rect.center)
        self.beam_timer = 8

    def draw_effect(self, screen: pg.Surface) -> None:
        """
        攻撃元から対象へ向かう光線を一定時間描画する
        引数 screen：画面Surface
        """
        super().draw_effect(screen)
        if self.beam_timer > 0:
            pg.draw.line(screen, (255, 255, 0), self.beam[0], self.beam[1], 3)
            self.beam_timer -= 1


class StopperUnit(Unit):
    """
    足止めユニット：攻撃した相手ユニットをしばらく動けなくする
    """
    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        通常のダメージに加え，対象がユニットなら足止めする（城は足止めされない）
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        super().attack(target, opponents)
        if isinstance(target, Unit):
            target.stun = self.spec["stun"]


class BossUnit(Unit):
    """
    ボスユニット：HPが半分以下になると怒りモードになり，強化されて手下を呼ぶ
    """
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__(spec, is_cat, x)
        self.enraged = False

    def update(self, opponents: pg.sprite.Group, base: Base) -> None:
        """
        HPを見て怒りモードへ移行してから，通常の更新を行う
        引数 opponents：相手側ユニットのグループ
        引数 base：相手側の城
        """
        if not self.enraged and 0 < self.hp <= self.spec["hp"] / 2:
            self.enrage()
        super().update(opponents, base)

    def enrage(self) -> None:
        """
        攻撃力，速度，攻撃頻度を上げ，見た目を赤くし，手下を2体呼ぶ
        """
        self.enraged = True
        self.spec = dict(self.spec)  # 共通の性能データを書き換えないようコピーする
        self.spec["atk"] = int(self.spec["atk"] * 1.5)
        self.spec["speed"] *= 1.8
        self.spec["interval"] = int(self.spec["interval"] * 0.6)
        self.image.fill((255, 0, 0))
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)
        for group in self.groups():
            for i in range(2):
                group.add(create_unit(ENEMY_SPECS[0], False, self.rect.left - 50 * i))

def push_back(unit: Unit, dist: int) -> None:
    """
    対象ユニットを進行方向と逆向きに押し戻し，攻撃のタイミングをリセットする
    （ボスは押し戻されない）
    引数 unit：押し戻す対象のユニット
    引数 dist：押し戻す距離（ピクセル）
    """
    if isinstance(unit, BossUnit):
        return
    unit.x = max(0, min(WIDTH, unit.x - unit.dir * dist))
    unit.rect.centerx = int(unit.x)
    unit.atk_timer = 0            


class WarshipUnit(Unit):
    """
    飛行戦艦ユニット：空中を進み，長射程の範囲攻撃で相手をふっとばす．
    一定回数攻撃するごとに，自分を中心とした広範囲の爆波を放つ
    """
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__(spec, is_cat, x)
        self.rect.bottom = GROUND_Y - spec["fly"]  # 地面から浮かせる
        self.atk_count = 0  # 攻撃した回数
        self.blast_pos = (0, 0)  # 爆発演出の中心座標
        self.blast_radius = 0  # 爆発演出の半径
        self.blast_timer = 0  # 爆発演出の残りフレーム数

    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        範囲内の相手全員にダメージを与えて押し戻す．
        blast_every回目の攻撃は，自分を中心とした広範囲の爆波になる
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        self.atk_count += 1
        if self.atk_count % self.spec["blast_every"] == 0:
            center_x, radius = self.rect.centerx, self.spec["blast_area"]
            damage = self.spec["atk"] * 2
        else:
            center_x, radius = target.rect.centerx, self.spec["area"]
            damage = self.spec["atk"]
        target.hp -= damage
        if isinstance(target, Unit):
            self.knock_back(target)
        for opp in opponents:
            if opp is not target and abs(opp.rect.centerx - center_x) <= radius:
                opp.hp -= damage
                self.knock_back(opp)
        self.blast_pos = (center_x, GROUND_Y - 20)
        self.blast_radius = radius
        self.blast_timer = 10

    def knock_back(self, unit: Unit) -> None:
        """
        対象ユニットを押し戻す（距離はspecのknockbackで決まる）
        引数 unit：押し戻す対象のユニット
        """
        push_back(unit, self.spec["knockback"])

    def draw_effect(self, screen: pg.Surface) -> None:
        """
        爆発の範囲を示す円を一定時間描画する
        引数 screen：画面Surface
        """
        super().draw_effect(screen)
        if self.blast_timer > 0:
            pg.draw.circle(screen, (255, 80, 0), self.blast_pos, self.blast_radius, 5)
            self.blast_timer -= 1


class KesaranUnit(AreaUnit):
    """
    ケサラン（ケサランパサラン風）ユニット：ふわふわ浮かぶ丸い妨害役．
    打たれ弱いが射程がとても長く，範囲内の相手をふっとばして動きを止める
    """
    def __init__(self, spec: dict, is_cat: bool, x: int) -> None:
        super().__init__(spec, is_cat, x)
        w, h = spec["size"]
        self.image = pg.Surface((w, h), pg.SRCALPHA)  # 四角ではなく丸い見た目にする
        pg.draw.circle(self.image, spec["color"], (w // 2, h // 2), w // 2)
        pg.draw.circle(self.image, (0, 0, 0), (w // 2, h // 2), w // 2, 2)
        self.rect.bottom = GROUND_Y - spec["fly"]  # 地面から浮かせる

    def attack(self, target: "Unit | Base", opponents: pg.sprite.Group) -> None:
        """
        範囲ダメージを与えたあと，範囲内の相手ユニットをふっとばして足止めする
        引数 target：攻撃対象
        引数 opponents：相手側ユニットのグループ
        """
        super().attack(target, opponents)
        for opp in opponents:
            if abs(opp.rect.centerx - target.rect.centerx) <= self.spec["area"]:
                self.disrupt(opp)

    def disrupt(self, unit: Unit) -> None:
        """
        対象ユニットを押し戻し，足止めする（ボスには効かない）
        引数 unit：妨害する対象のユニット
        """
        if isinstance(unit, BossUnit):
            return
        push_back(unit, self.spec["knockback"])
        unit.stun = max(unit.stun, self.spec["stun"])


# 性能データのkindとクラスの対応表（kindがなければ通常のUnit）
UNIT_CLASSES = {
    "normal": Unit,
    "area": AreaUnit,
    "shooter": ShooterUnit,
    "stopper": StopperUnit,
    "boss": BossUnit,
    "warship": WarshipUnit,
    "kesaran": KesaranUnit,
}


def create_unit(spec: dict, is_cat: bool, x: int) -> Unit:
    """
    性能データのkindに応じたクラスでユニットを生成する
    引数 spec：ユニットの性能を表す辞書
    引数 is_cat：Trueなら味方，Falseなら敵
    引数 x：出現位置のx座標
    戻り値：生成したユニット
    """
    return UNIT_CLASSES[spec.get("kind", "normal")](spec, is_cat, x)

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
    per_row = (len(CAT_SPECS) + 1) // 2  # 1段あたりのボタン数
    return [pg.Rect(20 + (i % per_row) * 170, 510 + (i // per_row) * 70, 160, 62)
            for i in range(len(CAT_SPECS))]


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
    cats.add(create_unit(spec, True, cat_base.rect.left))
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
        screen.blit(name, (btn.left + 10, btn.top + 3))
        screen.blit(cost, (btn.left + 10, btn.top + 31))
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


def main() -> None:
    pg.display.set_caption("工科大戦争")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    font = get_font(20)
    big_font = get_font(90)
    clock = pg.time.Clock()

    cat_base, enemy_base = Base(True), Base(False)
    cats, enemies = pg.sprite.Group(), pg.sprite.Group()
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
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(event.pos):
                        try_spawn(i, wallet, cooldowns, cats, cat_base)

        wallet.update()
        for i in range(len(cooldowns)):
            cooldowns[i] = max(0, cooldowns[i] - 1)
        if tmr % ENEMY_INTERVAL == ENEMY_INTERVAL - 1:
            spec = random.choices(ENEMY_SPECS, weights=[3, 1, 1])[0]
            enemies.add(create_unit(spec, False, enemy_base.rect.right))
        if tmr == BOSS_TIME:
            enemies.add(create_unit(BOSS_SPEC, False, enemy_base.rect.right))
        cats.update(enemies, enemy_base)
        enemies.update(cats, cat_base)

        draw_field(screen)
        enemy_base.draw(screen)
        cat_base.draw(screen)
        cats.draw(screen)
        enemies.draw(screen)
        for unit in list(cats) + list(enemies):
            draw_hp_bar(screen, unit.rect, unit.hp, unit.spec["hp"])
            unit.draw_effect(screen)
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