"""
にゃんこ大戦争風ゲームの共通基本機能（ベース部分）＋追加機能（画像・アニメ・BGM・効果音）

右側の自陣から味方ユニット（ネコ）を出撃させ，左側の敵陣を攻略するゲーム．
お金は時間とともに増え，お金とクールダウンの許す範囲でユニットを出撃できる．
ユニットは敵に当たると立ち止まって攻撃し，敵陣のHPを0にすれば勝利．

操作：数字キー1～3，または画面下のボタンのクリックでユニットを出撃
      Mキーで音（BGM・効果音）のミュート切り替え

【追加機能】画像，歩行アニメ，攻撃時の効果音，BGM，ミュートキー
素材ファイルが見つからない場合は，元の四角形・無音のまま動作する．
"""
import functools
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

# ======================================================================
# 【追加機能】素材ファイルの設定（★ここだけ自分の素材に合わせて書き換える★）
# ======================================================================
IMG_DIR = "fig"  # 画像を入れるフォルダ名（このpyファイルと同じ場所に作る）
SND_DIR = "sound"  # 音を入れるフォルダ名（このpyファイルと同じ場所に作る）

# 背景画像（画面の上～地面までを埋める．使わない場合は "" にする）
BG_FILE = "bg.png"

# 城の画像（自陣・敵陣）
BASE_IMG_FILES = {
    "cat": "cat_base.png",  # ★自陣の画像ファイル名
    "enemy": "enemy_base.png",  # ★敵陣の画像ファイル名
}

# 素材の絵が向いている方向（Trueなら左向き，Falseなら右向き）
# 味方は左へ，敵は右へ進むので，素材の向きが逆なら自動で左右反転する
CAT_IMG_FACE_LEFT = True
ENEMY_IMG_FACE_LEFT = False

# 歩行アニメ：画像を切り替える間隔（フレーム数），攻撃ポーズを見せる長さ（フレーム数）
ANIM_INTERVAL = 10
ATK_POSE_FRAMES = 12

# 効果音（★ファイル名を自分の素材に合わせる．wavかoggがおすすめ）
SE_FILES = {
    "attack_cat": "se_attack_cat.wav",  # ★味方の攻撃音
    "attack_enemy": "se_attack_enemy.wav",  # ★敵の攻撃音
    "spawn": "se_spawn.wav",  # ★出撃音
    "win": "se_win.wav",  # ★勝利音
    "lose": "se_lose.wav",  # ★敗北音
}
BGM_FILE = "bgm.mp3"  # ★BGM（mp3，ogg，wavなど）
BGM_VOLUME = 0.4  # BGMの音量（0.0～1.0）
SE_VOLUME = 0.6  # 効果音の音量（0.0～1.0）
SE_MIN_INTERVAL = 80  # 同じ効果音を連続で鳴らさない最小間隔（ミリ秒）
# ======================================================================

# 味方ユニットの性能（追加機能として種類を増やしやすいように辞書で管理）
# "walk"：歩行アニメの画像ファイル名のリスト（1枚だけでもOK，何枚でも増やせる）
# "attack"：攻撃ポーズの画像ファイル名（使わない場合は ""）
CAT_SPECS = [
    {"name": "ネコ", "cost": 50, "hp": 100, "atk": 10, "speed": 2.0,
     "range": 20, "interval": 40, "cooldown": 100,
     "color": (255, 220, 160), "size": (100, 100),
     "walk": ["neko_walk1.png", "neko_walk2.png"],  # ★
     "attack": "neko_attack.png"},  # ★
    {"name": "タンク", "cost": 100, "hp": 500, "atk": 6, "speed": 1.2,
     "range": 20, "interval": 50, "cooldown": 200,
     "color": (200, 200, 255), "size": (150, 170),
     "walk": ["tank_walk1.png", "tank_walk2.png"],  # ★
     "attack": "tank_attack.png"},  # ★
    {"name": "キック", "cost": 150, "hp": 120, "atk": 35, "speed": 1.8,
     "range": 60, "interval": 70, "cooldown": 250,
     "color": (255, 150, 150), "size": (140, 160),
     "walk": ["kick_walk1.png", "kick_walk2.png"],  # ★
     "attack": "kick_attack.png"},  # ★
]

# 敵ユニットの性能
ENEMY_SPECS = [
    {"name": "ワンコ", "hp": 120, "atk": 8, "speed": 1.5,
     "range": 20, "interval": 45,
     "color": (240, 240, 240), "size": (100, 100),
     "walk": ["wanko_walk1.png", "wanko_walk2.png"],  # ★
     "attack": "wanko_attack.png"},  # ★
    {"name": "ブタ", "hp": 500, "atk": 20, "speed": 1.0,
     "range": 20, "interval": 60,
     "color": (255, 170, 200), "size": (160, 180),
     "walk": ["buta_walk1.png", "buta_walk2.png"],  # ★
     "attack": "buta_attack.png"},  # ★
]


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


@functools.lru_cache(maxsize=None)
def load_image(filename: str, size: tuple, color: tuple,
               flip: bool = False, border: int = 2) -> pg.Surface:
    """
    画像を読み込んで指定サイズに拡縮する（同じ引数なら読み込み済みのものを使い回す）
    画像ファイルが見つからない場合は，元の四角形（色付き＋黒枠）で代用する
    引数 filename：IMG_DIR内の画像ファイル名
    引数 size：拡縮後の大きさ（幅，高さ）
    引数 color：代用の四角形の色
    引数 flip：Trueなら左右反転する
    引数 border：代用の四角形の枠線の太さ
    戻り値：画像のSurface
    """
    path = os.path.join(IMG_DIR, filename)
    try:
        img = pg.image.load(path).convert_alpha()
        img = pg.transform.smoothscale(img, size)
        return pg.transform.flip(img, True, False) if flip else img
    except (pg.error, FileNotFoundError):
        print(f"[画像なし] {path} が読み込めないため四角形で代用します")
        img = pg.Surface(size)
        img.fill(color)
        pg.draw.rect(img, (0, 0, 0), img.get_rect(), border)
        return img


def load_background() -> "pg.Surface | None":
    """
    背景画像を読み込む（空から地面までの大きさに拡縮する）
    戻り値：背景のSurface（設定なし，または読み込めない場合はNone）
    """
    if not BG_FILE:
        return None
    path = os.path.join(IMG_DIR, BG_FILE)
    try:
        img = pg.image.load(path).convert()
        return pg.transform.smoothscale(img, (WIDTH, GROUND_Y))
    except (pg.error, FileNotFoundError):
        print(f"[画像なし] {path} が読み込めないため背景は単色にします")
        return None


class SoundManager:
    """
    BGM・効果音・ミュートに関するクラス
    音声ファイルや音声デバイスがない場合でも，エラーにならず無音で動作する
    """
    def __init__(self) -> None:
        self.muted = False
        self.enabled = True  # 音声デバイスが使えるか
        self.ses: dict[str, pg.mixer.Sound] = {}
        self.last_play: dict[str, int] = {}  # 効果音ごとの最後に鳴らした時刻（ミリ秒）
        try:
            pg.mixer.init()
        except pg.error:
            print("[音なし] 音声デバイスが使えないため無音で動作します")
            self.enabled = False
            return
        for name, filename in SE_FILES.items():
            try:
                snd = pg.mixer.Sound(os.path.join(SND_DIR, filename))
                snd.set_volume(SE_VOLUME)
                self.ses[name] = snd
            except (pg.error, FileNotFoundError):
                print(f"[音なし] {os.path.join(SND_DIR, filename)} が読み込めません")

    def play_bgm(self) -> None:
        """
        BGMをループ再生する（ミュート中は音量0で再生しておく）
        """
        if not self.enabled:
            return
        try:
            pg.mixer.music.load(os.path.join(SND_DIR, BGM_FILE))
            pg.mixer.music.set_volume(0 if self.muted else BGM_VOLUME)
            pg.mixer.music.play(loops=-1)
        except (pg.error, FileNotFoundError):
            print(f"[音なし] {os.path.join(SND_DIR, BGM_FILE)} が読み込めません")

    def stop_bgm(self) -> None:
        """
        BGMを停止する
        """
        if self.enabled:
            pg.mixer.music.stop()

    def play_se(self, name: str) -> None:
        """
        効果音を1回鳴らす（ミュート中，または直前に鳴らしたばかりなら鳴らさない）
        引数 name：SE_FILESのキー名
        """
        if not self.enabled or self.muted or name not in self.ses:
            return
        now = pg.time.get_ticks()
        if now - self.last_play.get(name, -SE_MIN_INTERVAL) < SE_MIN_INTERVAL:
            return
        self.ses[name].play()
        self.last_play[name] = now

    def toggle_mute(self) -> None:
        """
        ミュートのON/OFFを切り替える
        """
        self.muted = not self.muted
        if not self.enabled:
            return
        pg.mixer.music.set_volume(0 if self.muted else BGM_VOLUME)
        if self.muted:
            pg.mixer.stop()  # 鳴っている効果音も止める


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
        self.image = load_image(
            BASE_IMG_FILES["cat" if is_cat else "enemy"], (80, 200),
            (100, 150, 255) if is_cat else (255, 120, 120), border=3
        )
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
        self.is_cat = is_cat
        self.dir = -1 if is_cat else +1
        self.atk_timer = spec["interval"]  # 最初の1発はすぐ撃てるようにする
        self.anim_timer = 0  # 歩行アニメ用のカウンタ（歩いたフレーム数）

        # 素材の向きと進行方向が逆なら左右反転する
        face_left = CAT_IMG_FACE_LEFT if is_cat else ENEMY_IMG_FACE_LEFT
        flip = face_left != (self.dir < 0)
        self.walk_imgs = [
            load_image(f, spec["size"], spec["color"], flip) for f in spec["walk"]
        ]
        self.atk_img = (
            load_image(spec["attack"], spec["size"], spec["color"], flip)
            if spec.get("attack") else None
        )
        self.image = self.walk_imgs[0]
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

    def animate(self, target: "Unit | Base | None") -> None:
        """
        状況に応じて表示する画像を切り替える
        歩行中は歩行画像を順番に切り替え，攻撃した直後は攻撃ポーズ，それ以外は立ち絵にする
        引数 target：現在の攻撃対象（歩行中ならNone）
        """
        if target is None:
            idx = (self.anim_timer // ANIM_INTERVAL) % len(self.walk_imgs)
            self.image = self.walk_imgs[idx]
        elif self.atk_img is not None and self.atk_timer < ATK_POSE_FRAMES:
            self.image = self.atk_img
        else:
            self.image = self.walk_imgs[0]

    def update(self, opponents: pg.sprite.Group, base: Base, sounds: SoundManager) -> None:
        """
        HP判定，攻撃，移動，アニメーションを行う
        引数 opponents：相手側ユニットのグループ
        引数 base：相手側の城
        引数 sounds：効果音を鳴らすためのSoundManager
        """
        if self.hp <= 0:
            self.kill()
            return
        target = self.find_target(opponents, base)
        if target is None:
            self.x += self.dir * self.spec["speed"]
            self.rect.centerx = int(self.x)
            self.anim_timer += 1
        else:
            self.atk_timer += 1
            if self.atk_timer >= self.spec["interval"]:
                target.hp -= self.spec["atk"]
                self.atk_timer = 0
                sounds.play_se("attack_cat" if self.is_cat else "attack_enemy")
        self.animate(target)


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
              cats: pg.sprite.Group, cat_base: Base, sounds: SoundManager) -> None:
    """
    お金とクールダウンの条件を満たせば，味方ユニットを出撃させる
    引数 idx：CAT_SPECSの番号
    引数 wallet：所持金
    引数 cooldowns：ユニットごとの残りクールダウン（フレーム数）
    引数 cats：味方ユニットのグループ
    引数 cat_base：自陣
    引数 sounds：出撃音を鳴らすためのSoundManager
    """
    spec = CAT_SPECS[idx]
    if cooldowns[idx] > 0 or not wallet.pay(spec["cost"]):
        return
    cats.add(Unit(spec, True, cat_base.rect.left))
    cooldowns[idx] = spec["cooldown"]
    sounds.play_se("spawn")


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


def draw_sound_status(screen: pg.Surface, font: pg.font.Font, sounds: SoundManager) -> None:
    """
    音の状態（ON/OFF）とミュートキーの案内を左上に描画する
    引数 screen：画面Surface
    引数 font：表示用フォント
    引数 sounds：音を管理するSoundManager
    """
    if not sounds.enabled:
        label = "音：使用不可"
    else:
        label = f"M：音 {'OFF' if sounds.muted else 'ON'}"
    screen.blit(font.render(label, True, (0, 0, 0)), (20, 20))


def draw_field(screen: pg.Surface, bg: "pg.Surface | None") -> None:
    """
    背景（空と地面）を描画する
    引数 screen：画面Surface
    引数 bg：背景画像（Noneなら単色の空）
    """
    screen.fill((135, 206, 235))
    if bg is not None:
        screen.blit(bg, (0, 0))
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
    pg.display.set_caption("ネコ大戦争（仮）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    font = get_font(26)
    big_font = get_font(90)
    clock = pg.time.Clock()

    bg = load_background()
    sounds = SoundManager()
    sounds.play_bgm()

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
            if event.type == pg.KEYDOWN and event.key == pg.K_m:
                sounds.toggle_mute()
            if event.type == pg.KEYDOWN and pg.K_1 <= event.key < pg.K_1 + len(CAT_SPECS):
                try_spawn(event.key - pg.K_1, wallet, cooldowns, cats, cat_base, sounds)
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(event.pos):
                        try_spawn(i, wallet, cooldowns, cats, cat_base, sounds)

        wallet.update()
        for i in range(len(cooldowns)):
            cooldowns[i] = max(0, cooldowns[i] - 1)
        if tmr % ENEMY_INTERVAL == ENEMY_INTERVAL - 1:
            spec = random.choices(ENEMY_SPECS, weights=[3, 1])[0]
            enemies.add(Unit(spec, False, enemy_base.rect.right))
        cats.update(enemies, enemy_base, sounds)
        enemies.update(cats, cat_base, sounds)

        draw_field(screen, bg)
        enemy_base.draw(screen)
        cat_base.draw(screen)
        cats.draw(screen)
        enemies.draw(screen)
        for unit in list(cats) + list(enemies):
            draw_hp_bar(screen, unit.rect, unit.hp, unit.spec["hp"])
        draw_ui(screen, font, wallet, cooldowns, buttons)
        draw_sound_status(screen, font, sounds)

        if enemy_base.hp <= 0:
            sounds.stop_bgm()
            sounds.play_se("win")
            show_result(screen, big_font, "勝利！")
            return
        if cat_base.hp <= 0:
            sounds.stop_bgm()
            sounds.play_se("lose")
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
