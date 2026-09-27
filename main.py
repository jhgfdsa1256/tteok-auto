#!/usr/bin/env python3
"""
마피아42 떡치기 게임 Kivy 앱 (Android)
Pillow 기반 색상 매칭 + 플로팅 팝업
(opencv/numpy 제거 - Android 빌드 안정성을 위해 Pillow만 사용)
"""

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock

import threading
import time
import sqlite3
import colorsys
from datetime import datetime
from pathlib import Path

try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False
    print("Android 모듈을 찾을 수 없습니다 (데스크톱 모드)")

DB_PATH = Path("/sdcard/Download/game_logs.db") if ANDROID else Path("game_logs.db")


class GameDatabase:
    """게임 로그 저장소"""

    def __init__(self):
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_sessions (
                        id INTEGER PRIMARY KEY,
                        timestamp TEXT,
                        total_rounds INTEGER,
                        success_count INTEGER,
                        failed_count INTEGER
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY,
                        session_id INTEGER,
                        timestamp TEXT,
                        job_state TEXT,
                        detected_pattern TEXT,
                        button_clicked TEXT,
                        result TEXT,
                        FOREIGN KEY (session_id) REFERENCES game_sessions(id)
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"DB 초기화 오류: {e}")

    def save_session(self, total_rounds, success_count, failed_count):
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO game_sessions
                    (timestamp, total_rounds, success_count, failed_count)
                    VALUES (?, ?, ?, ?)
                """, (datetime.now().isoformat(), total_rounds, success_count, failed_count))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"세션 저장 오류: {e}")
            return None

    def save_prediction(self, session_id, job_state, pattern, button, result):
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute("""
                    INSERT INTO predictions
                    (session_id, timestamp, job_state, detected_pattern, button_clicked, result)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, datetime.now().isoformat(), job_state, pattern, button, result))
                conn.commit()
        except Exception as e:
            print(f"예측 저장 오류: {e}")


class ColorAnalyzer:
    """
    Pillow(PIL) 기반 색상 분석
    opencv/numpy 없이 픽셀 단위로 직접 HSV 변환 및 판단.
    고정 그리드 방식: 하단 버튼은 항상 같은 상대 위치에 있다고 가정하고
    각 슬롯의 평균 색상만 샘플링 (윤곽 감지보다 훨씬 가볍고 안정적)
    """

    def __init__(self):
        self.db = GameDatabase()

        # HSV 범위 (0~1 스케일)
        self.rabbit_h_range = (85 / 180, 130 / 180)
        self.pig_h_range1 = (0 / 180, 25 / 180)
        self.pig_h_range2 = (130 / 180, 180 / 180)

        # 6개 버튼 슬롯 상대 좌표 (left, top, right, bottom), 0~1 비율
        self.button_slots = [
            (0.15, 0.75, 0.30, 0.85),
            (0.45, 0.75, 0.60, 0.85),
            (0.70, 0.75, 0.85, 0.85),
            (0.15, 0.87, 0.30, 0.97),
            (0.45, 0.87, 0.60, 0.97),
            (0.70, 0.87, 0.85, 0.97),
        ]

        self.toolbar_region = (0.0, 0.85, 1.0, 1.0)

    def _sample_average_color(self, img, region):
        w, h = img.size
        left = int(region[0] * w)
        top = int(region[1] * h)
        right = int(region[2] * w)
        bottom = int(region[3] * h)

        if right <= left or bottom <= top:
            return None

        crop = img.crop((left, top, right, bottom))
        crop = crop.resize((8, 8))
        pixels = list(crop.getdata())

        if not pixels:
            return None

        r = sum(p[0] for p in pixels) / len(pixels)
        g = sum(p[1] for p in pixels) / len(pixels)
        b = sum(p[2] for p in pixels) / len(pixels)
        return (r, g, b)

    def _classify_color(self, rgb):
        if rgb is None:
            return "빈칸"

        r, g, b = [c / 255.0 for c in rgb]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        if s < 0.15:
            return "빈칸"

        if self.rabbit_h_range[0] <= h <= self.rabbit_h_range[1]:
            return "토끼"

        if (self.pig_h_range1[0] <= h <= self.pig_h_range1[1] or
                self.pig_h_range2[0] <= h <= self.pig_h_range2[1]):
            return "돼지"

        return "빈칸"

    def detect_job_state(self, img):
        if img is None:
            return "대기"
        rgb = self._sample_average_color(img, self.toolbar_region)
        result = self._classify_color(rgb)
        return "대기" if result == "빈칸" else result

    def detect_buttons(self, img):
        if img is None:
            return []

        buttons = []
        for idx, slot in enumerate(self.button_slots):
            rgb = self._sample_average_color(img, slot)
            job = self._classify_color(rgb)
            if job != "빈칸":
                buttons.append({'slot_index': idx, 'region': slot, 'job': job})
        return buttons

    def detect_top_pattern(self, img):
        if img is None:
            return "없음"
        region = (0.0, 0.0, 1.0, 0.2)
        rgb = self._sample_average_color(img, region)
        if rgb is None:
            return "없음"
        brightness = sum(rgb) / 3
        return "패턴(밝음)" if brightness > 150 else "패턴(어두움)"

    def decide_button(self, job_state, available_buttons):
        if job_state == "대기" or not available_buttons:
            return None
        matching = [b for b in available_buttons if b['job'] == job_state]
        return matching[0] if matching else None


class FloatingPopup(FloatLayout):
    """플로팅 팝업"""

    def __init__(self, analyzer, **kwargs):
        super().__init__(**kwargs)
        self.analyzer = analyzer
        self.running = False
        self.session_id = None
        self.round_count = 0
        self.success_count = 0
        self.is_expanded = False

        self.btn_expand = Button(
            text='⊕', size_hint=(None, None), size=(60, 60),
            pos_hint={'right': 1, 'top': 1}
        )
        self.btn_expand.bind(on_press=self.expand)
        self.add_widget(self.btn_expand)

    def expand(self, instance):
        if not self.is_expanded:
            self.is_expanded = True
            self.clear_widgets()
            self.create_expanded_ui()

    def create_expanded_ui(self):
        main_box = BoxLayout(orientation='vertical', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        top_bar = BoxLayout(size_hint_y=0.1, padding=5, spacing=5)
        top_bar.add_widget(Label(text='🎮 떡치기', size_hint_x=0.7))

        btn_min = Button(text='_', size_hint_x=0.15)
        btn_min.bind(on_press=self.minimize)
        top_bar.add_widget(btn_min)

        btn_close = Button(text='✕', size_hint_x=0.15)
        btn_close.bind(on_press=self.close)
        top_bar.add_widget(btn_close)

        main_box.add_widget(top_bar)

        info_box = BoxLayout(orientation='vertical', size_hint_y=0.6, padding=10, spacing=5)
        self.label_status = Label(text='상태: 대기', size_hint_y=0.2)
        info_box.add_widget(self.label_status)
        self.label_button = Label(text='다음 버튼: -', size_hint_y=0.2)
        info_box.add_widget(self.label_button)
        self.label_stats = Label(text='라운드: 0 | 성공: 0', size_hint_y=0.2)
        info_box.add_widget(self.label_stats)
        main_box.add_widget(info_box)

        btn_box = BoxLayout(size_hint_y=0.2, spacing=5, padding=5)
        self.btn_start = Button(text='▶ 시작')
        self.btn_start.bind(on_press=self.start_game)
        btn_box.add_widget(self.btn_start)
        self.btn_stop = Button(text='⏹ 정지')
        self.btn_stop.bind(on_press=self.stop_game)
        btn_box.add_widget(self.btn_stop)
        main_box.add_widget(btn_box)

        self.add_widget(main_box)

    def minimize(self, instance):
        if self.is_expanded:
            self.is_expanded = False
            self.clear_widgets()
            self.btn_expand = Button(
                text='⊕', size_hint=(None, None), size=(60, 60),
                pos_hint={'right': 1, 'top': 1}
            )
            self.btn_expand.bind(on_press=self.expand)
            self.add_widget(self.btn_expand)

    def close(self, instance):
        if self.running:
            self.stop_game(None)
        if self.parent:
            self.parent.remove_widget(self)

    def start_game(self, instance):
        self.running = True
        self.btn_start.disabled = True
        self.round_count = 0
        self.success_count = 0
        self.session_id = self.analyzer.db.save_session(0, 0, 0)
        thread = threading.Thread(target=self.game_loop, daemon=True)
        thread.start()

    def stop_game(self, instance):
        self.running = False
        self.btn_start.disabled = False

    def game_loop(self):
        last_update = time.time()

        while self.running:
            start_time = time.time()
            try:
                img = self.capture_screen()

                if img is not None:
                    job_state = self.analyzer.detect_job_state(img)

                    if job_state != "대기":
                        pattern = self.analyzer.detect_top_pattern(img)
                        buttons = self.analyzer.detect_buttons(img)
                        button = self.analyzer.decide_button(job_state, buttons)

                        button_color_map = {'토끼': '청/초/파', '돼지': '빨/주/노/핑/보'}
                        button_color = button_color_map.get(job_state, '-')

                        if time.time() - last_update > 0.1:
                            Clock.schedule_once(
                                lambda dt, s=job_state, c=button_color, p=pattern:
                                    self.update_ui(s, c, p), 0
                            )
                            last_update = time.time()

                        if button:
                            self.click_button(button)
                            self.success_count += 1
                            self.round_count += 1
                            self.analyzer.db.save_prediction(
                                self.session_id, job_state, pattern, button_color, "성공"
                            )
                    else:
                        if time.time() - last_update > 0.1:
                            Clock.schedule_once(lambda dt: self.update_ui("대기", "-", "-"), 0)
                            last_update = time.time()

                elapsed = time.time() - start_time
                sleep_time = max(0.01 - elapsed, 0)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"게임 루프 오류: {e}")
                self.running = False

    def capture_screen(self):
        """화면 캡처 - 실제 구현은 별도 권한/API 필요 (현재 테스트 모드)"""
        return None

    def click_button(self, button):
        """버튼 클릭 - 실제 구현은 별도 권한/API 필요 (현재 테스트 모드)"""
        pass

    def update_ui(self, state, button_color, pattern):
        if self.is_expanded:
            self.label_status.text = f'상태: {state}'
            self.label_button.text = f'다음 버튼: {button_color}'
            self.label_stats.text = f'라운드: {self.round_count} | 성공: {self.success_count}'


class Mafia42App(App):
    """메인 앱"""

    def build(self):
        Window.size = (400, 600)

        if ANDROID:
            request_permissions([
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])

        self.analyzer = ColorAnalyzer()

        main_layout = FloatLayout()
        bg_box = BoxLayout(orientation='vertical', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        title = Label(text='🎮 마피아42 떡치기 자동 플레이', size_hint_y=0.2, font_size='18sp')
        bg_box.add_widget(title)

        desc = Label(text='아래 버튼을 클릭하면 플로팅 팝업이 나타납니다', size_hint_y=0.1, font_size='12sp')
        bg_box.add_widget(desc)

        btn_start = Button(
            text='▶ 시작', size_hint_y=0.2, size_hint_x=0.6,
            pos_hint={'center_x': 0.5}
        )
        btn_start.bind(on_press=self.show_popup)
        bg_box.add_widget(btn_start)

        bg_box.add_widget(Label(size_hint_y=0.5))
        main_layout.add_widget(bg_box)

        return main_layout

    def show_popup(self, instance):
        popup = FloatingPopup(self.analyzer, size_hint=(0.5, 0.5), pos_hint={'right': 1, 'top': 1})
        self.root.add_widget(popup)


if __name__ == '__main__':
    Mafia42App().run()
