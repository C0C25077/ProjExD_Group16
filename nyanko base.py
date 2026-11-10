"""
にゃんこ大戦争風ゲーム（ベース＋コインキャッチ＋にゃんこ砲＋財布システム）

右側の自陣から味方ユニット（ネコ）を出撃させ，左側の敵陣を攻略するゲーム．
お金は時間とともに増え，お金とクールダウンの許す範囲でユニットを出撃できる．
ユニットは敵に当たると立ち止まって攻撃し，敵陣のHPを0にすれば勝利．

操作：
- 数字キー 1～7 または画面下ボタン：ユニット出撃
- Wキー / 0キー または画面右下ボタン：財布レベルアップ（お金の増加速度と上限アップ）
- 画面上から落ちるコインをクリック：キャッチしてお金が増加
- 自陣上の「準備OK！」をクリック：にゃんこ砲発射（画面内の敵全体にダメージ）
"""

import os
import random
import sys
import time
from typing import List, Optional

import pygame as pg

# 定数定義
WIDTH, HEIGHT = 1100, 650
GROUND_Y = 500  # 地面の高さ（ユニットの足元のy座標）
FPS = 50
ENEMY_INTERVAL = 150  # 敵が出現する間隔（フレーム数）
COIN_INTERVAL = 180   # コインが出現する間隔（フレーム数）
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

#------------------------------------------------------------------難易度（ステージ）の設定（追加機能3）
STAGE_SPECS = [
    {"name": "ノーマル", "rate": 1.0, "color": (100, 200, 100)},
    {"name": "ハード", "rate": 1.2, "color": (220, 80, 80)},
]
#------------------------------------------------------------------

# 味方ユニットの性能
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
]

#--------------------------------------------------------- ボスユニットの性能（追加機能3）ボスの追加
BOSS_SPEC = {
    "name": "ボス", "hp": 1500, "atk": 40, "speed": 0.8,
    "range": 40, "interval": 80,
    "color": (150, 75, 0), "size": (90, 120)
}
#----------------------------------------------------------

def get_font(size: int) -> pg.font.Font:
    """日本語を表示できるフォントを探して返す.

    Args:
        size (int): フォントサイズ

    Returns:
        pg.font.Font: Fontオブジェクト（見つからない場合は標準フォント）
    """
    name = pg.font.match_font(
        "meiryo,yugothic,msgothic,notosanscjkjp,hiraginosans,takaopgothic"
    )
    return pg.font.Font(name, size)

def draw_hp_bar(screen: pg.Surface, rct: pg.Rect, hp: int, max_hp: int) -> None:
    """対象の頭上にHPバーを描画する.

    Args:
        screen (pg.Surface): 画面Surface
        rct (pg.Rect): 対象のRect
        hp (int): 現在のHP
        max_hp (int): 最大HP
    """
    ratio = max(0, hp) / max_hp
    bar = pg.Rect(rct.left, rct.top - 10, rct.width, 6)
    pg.draw.rect(screen, (80, 80, 80), bar)
    pg.draw.rect(screen, (0, 0, 0), bar, 1)
    pg.draw.rect(
        screen,
        (0, 200, 0),
        (bar.left, bar.top, int(bar.width * ratio), bar.height),
    )


class Base:
    """自陣・敵陣（城）に関するクラス."""

    def __init__(self, is_cat: bool) -> None:
        """引数 is_cat：Trueなら自陣（右側），Falseなら敵陣（左側）."""
        self.hp = BASE_HP
        self.max_hp = BASE_HP
        self.image = pg.Surface((80, 200))
        self.image.fill((100, 150, 255) if is_cat else (255, 120, 120))
        pg.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 3)
        self.rect = self.image.get_rect()
        self.rect.bottom = GROUND_Y
        self.rect.centerx = WIDTH - 80 if is_cat else 80

    def draw(self, screen: pg.Surface) -> None:
        """城とHPバーを描画する.

        Args:
            screen (pg.Surface): 画面Surface
        """
        screen.blit(self.image, self.rect)
        draw_hp_bar(screen, self.rect, self.hp, self.max_hp)


class Unit(pg.sprite.Sprite):
    """味方・敵のユニットに関するクラス."""

    def __init__(self, spec: dict, is_cat: bool, x: int, rate: float = 1.0) -> None:
        """ユニット初期化.

        Args:
            spec (dict): ユニットの性能を表す辞書
            is_cat (bool): Trueなら味方（左へ進む），Falseなら敵（右へ進む）
            x (int): 出現位置のx座標
        引数 rate：敵ユニットのステータス倍率（ハード時 1.2）
        """
        super().__init__()
        self.spec = spec.copy()
        if not is_cat:  # 敵の場合はステータス（HP・攻撃力）を強化
            self.spec["hp"] = int(spec["hp"] * rate)
            self.spec["atk"] = int(spec["atk"] * rate)

        self.hp = self.spec["hp"]
        self.dir = -1 if is_cat else +1
        self.stun = 0  # 足止めされている残りフレーム数
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
        self.x = float(self.rect.centerx)

    def can_reach(self, rct: pg.Rect) -> bool:
        """対象のRectが攻撃射程内にあるかを判定する.

        Args:
            rct (pg.Rect): 敵ユニットまたは敵陣のRect

        Returns:
            bool: 射程内ならTrue
        """
        if self.dir < 0:
            return rct.right >= self.rect.left - self.spec["range"]
        return rct.left <= self.rect.right + self.spec["range"]

    def find_target(
        self, opponents: pg.sprite.Group, base: Base
    ) -> Optional["Unit | Base"]:
        """攻撃対象を探す（射程内のユニットのうち最も近いもの，いなければ敵城）.

        Args:
            opponents (pg.sprite.Group): 相手側ユニットのグループ
            base (Base): 相手側の城

        Returns:
            Optional[Unit | Base]: 攻撃対象（いなければNone）
        """
        cands = [o for o in opponents if self.can_reach(o.rect)]
        if cands:
            return min(cands, key=lambda o: abs(o.rect.centerx - self.rect.centerx))
        if self.can_reach(base.rect):
            return base
        return None

    def update(self, opponents: pg.sprite.Group, base: Base) -> None:
        """HP判定，攻撃，移動を行う.

        Args:
            opponents (pg.sprite.Group): 相手側ユニットのグループ
            base (Base): 相手側の城
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
    """お金（所持金）および財布のレベルアップに関するクラス."""

    def __init__(self) -> None:
        """初期パラメータの設定."""
        self.money = 100.0
        self.level = 1
        self.max_level = 8
        self.max_money = 500  # 初期上限
        self.income = 0.4  # 1フレームあたりの初期増加量

    def update(self) -> None:
        """お金を時間経過で増やす（上限あり）."""
        self.money = min(float(self.max_money), self.money + self.income)

    def add_money(self, amount: int) -> None:
        """コイン取得などでお金を増やす"""
        self.money = min(float(self.max_money), self.money + amount)

    def pay(self, cost: int) -> bool:
        """所持金が足りれば支払う.

        Args:
            cost (int): 支払う金額

        Returns:
            bool: 支払えたらTrue，足りなければFalse
        """
        if self.money < cost:
            return False
        self.money -= cost
        return True

    def get_level_up_cost(self) -> int:
        """現在のレベルに応じたレベルアップに必要な費用を取得する.

        Returns:
            int: レベルアップに必要な費用（最大レベルの場合は0）
        """
        if self.level >= self.max_level:
            return 0
        return 100 * self.level

    def level_up(self) -> bool:
        """所持金が足りれば財布レベルを上げ，所持金上限と増加速度を強化する.

        Returns:
            bool: レベルアップに成功したらTrue，失敗・レベルMAXならFalse
        """
        if self.level >= self.max_level:
            return False
        cost = self.get_level_up_cost()
        if not self.pay(cost):
            return False

        self.level += 1
        self.max_money += 350  # 所持金上限の増加
        self.income += 0.35   # 毎フレームの収入増加量アップ
        return True


def make_buttons() -> List[pg.Rect]:
    """出撃ボタンのRectのリストを作る.

    Returns:
        List[pg.Rect]: 味方ユニットの種類ごとのボタンRect
    """
    per_row = (len(CAT_SPECS) + 1) // 2  # 1段あたりのボタン数
    return [pg.Rect(20 + (i % per_row) * 170, 510 + (i // per_row) * 70, 160, 62)
            for i in range(len(CAT_SPECS))]


def make_wallet_button() -> pg.Rect:
    """財布レベルアップボタンのRectを作る.

    Returns:
        pg.Rect: 財布レベルアップボタンのRect
    """
    return pg.Rect(WIDTH - 180, 540, 160, 90)


def try_spawn(
    idx: int,
    wallet: Wallet,
    cooldowns: List[int],
    cats: pg.sprite.Group,
    cat_base: Base,
) -> None:
    """お金とクールダウンの条件を満たせば，味方ユニットを出撃させる.

    Args:
        idx (int): CAT_SPECSの番号
        wallet (Wallet): 所持金オブジェクト
        cooldowns (List[int]): ユニットごとの残りクールダウン
        cats (pg.sprite.Group): 味方ユニットのグループ
        cat_base (Base): 自陣
    """
    spec = CAT_SPECS[idx]
    if cooldowns[idx] > 0 or not wallet.pay(spec["cost"]):
        return
    cats.add(create_unit(spec, True, cat_base.rect.left))
    cooldowns[idx] = spec["cooldown"]


def draw_ui(
    screen: pg.Surface,
    font: pg.font.Font,
    wallet: Wallet,
    cooldowns: List[int],
    buttons: List[pg.Rect],
    wallet_btn: pg.Rect,
) -> None:
    """所持金表示・出撃ボタン・財布レベルアップボタンを描画する.

    Args:
        screen (pg.Surface): 画面Surface
        font (pg.font.Font): 表示用フォント
        wallet (Wallet): 所持金オブジェクト
        cooldowns (List[int]): ユニットごとの残りクールダウン
        buttons (List[pg.Rect]): 出撃ボタンのRectリスト
        wallet_btn (pg.Rect): 財布レベルアップボタンのRect
    """
    # ユニット出撃ボタン描画
    for i, (spec, btn) in enumerate(zip(CAT_SPECS, buttons)):
        usable = cooldowns[i] == 0 and wallet.money >= spec["cost"]
        pg.draw.rect(screen, (255, 230, 120) if usable else (150, 150, 150), btn)
        if cooldowns[i] > 0:
            h = int(btn.height * cooldowns[i] / spec["cooldown"])
            pg.draw.rect(screen, (90, 90, 90), (btn.left, btn.top, btn.width, h))
        pg.draw.rect(screen, (0, 0, 0), btn, 3)
        name = font.render(f"{i + 1}:{spec['name']}", True, (0, 0, 0))
        cost = font.render(f"{spec['cost']}円", True, (0, 0, 0))
        screen.blit(name, (btn.left + 10, btn.top + 5))
        screen.blit(cost, (btn.left + 10, btn.top + 32))

    # 財布レベルアップボタン描画
    cost_level_up = wallet.get_level_up_cost()
    is_max = wallet.level >= wallet.max_level
    can_level_up = not is_max and wallet.money >= cost_level_up

    pg.draw.rect(
        screen, (100, 220, 100) if can_level_up else (160, 160, 160), wallet_btn
    )
    pg.draw.rect(screen, (0, 0, 0), wallet_btn, 3)

    btn_lbl = font.render("[W/0]財布", True, (0, 0, 0))
    if is_max:
        cost_lbl = font.render("レベル MAX", True, (0, 0, 0))
    else:
        cost_lbl = font.render(f"{cost_level_up}円", True, (0, 0, 0))

    screen.blit(btn_lbl, (wallet_btn.left + 8, wallet_btn.top + 10))
    screen.blit(cost_lbl, (wallet_btn.left + 10, wallet_btn.top + 50))

    # 所持金および財布LV表示
    money_str = f"お金 {int(wallet.money)} / {wallet.max_money}円 (Lv.{wallet.level})"
    money = font.render(money_str, True, (0, 0, 0))
    screen.blit(money, (WIDTH - money.get_width() - 20, 20))


def draw_field(screen: pg.Surface) -> None:
    """背景（空と地面）を描画する.

    Args:
        screen (pg.Surface): 画面Surface
    """
    screen.fill((135, 206, 235))
    pg.draw.rect(screen, (150, 110, 70), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pg.draw.line(screen, (0, 0, 0), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)


def show_result(screen: pg.Surface, font: pg.font.Font, message: str) -> None:
    """勝敗の結果を3秒間表示する.

    Args:
        screen (pg.Surface): 画面Surface
        font (pg.font.Font): 表示用フォント
        message (str): 表示する文字列
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
    pg.display.set_caption("工科大戦争")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    font = get_font(24)
    btn_font = get_font(20)
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
    coins = pg.sprite.Group()
    cannon = CatCannon(cat_base)  # にゃんこ砲生成
    wallet = Wallet()
    cooldowns = [0] * len(CAT_SPECS)
    buttons = make_buttons()
    wallet_btn = make_wallet_button()
    tmr = 0
    #------------------------------------------------------------------
    boss_spawned = False  # ボスが出現済みか管理するフラグ（追加機能3）
    #-------------------------------------------------------------------
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return

            if event.type == pg.KEYDOWN:
                # 数字キー 1～len(CAT_SPECS) で出撃
                if pg.K_1 <= event.key < pg.K_1 + len(CAT_SPECS):
                    try_spawn(event.key - pg.K_1, wallet, cooldowns, cats, cat_base)
                # Wキーまたは 0 キーで財布レベルアップ
                elif event.key in (pg.K_w, pg.K_0, pg.K_KP0):
                    wallet.level_up()

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

                # 3. 出撃ボタン・財布ボタン判定
                if not clicked_coin:
                    for i, btn in enumerate(buttons):
                        if btn.collidepoint(event.pos):
                            try_spawn(i, wallet, cooldowns, cats, cat_base)
                    
                    if wallet_btn.collidepoint(event.pos):
                        wallet.level_up()

        wallet.update()
        cannon.update()  # にゃんこ砲のチャージ更新

        for i in range(len(cooldowns)):
            cooldowns[i] = max(0, cooldowns[i] - 1)
        if tmr % ENEMY_INTERVAL == ENEMY_INTERVAL - 1:
            spec = random.choices(ENEMY_SPECS, weights=[3, 1])[0]
            enemies.add(Unit(spec, False, enemy_base.rect.right))
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
            if isinstance(unit, Unit):
                draw_hp_bar(screen, unit.rect, unit.hp, unit.spec["hp"])
                if hasattr(unit, "draw_effect"):
                    unit.draw_effect(screen)
        
        draw_ui(screen, font, wallet, cooldowns, buttons, wallet_btn)
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