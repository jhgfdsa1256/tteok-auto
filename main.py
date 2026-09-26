#!/usr/bin/env python3
"""
마피아42 떡치기 게임 Kivy 앱 (Android)
색상 기반 버튼 인식 + 플로팅 팝업 + 접근성 서비스
"""

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.uix.image import Image

import threading
import time
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from pathlib import Path
import json

# Android 관련 임포트 (조건부)
try:
    from android.permissions import request_permissions, Permission
    from android.runnable import run_on_ui_thread
    ANDROID = True
except ImportError:
    ANDROID = False
    print("Android 모듈을 찾을 수 없습니다 (데스크톱 모드)")

# 화면 캡처 (Android)
try:
    from jnius import autoclass
    PythonJavaClass = autoclass('org.kivy.android.PythonJavaClass')
    JNIUS_AVAILABLE = True
except:
    JNIUS_AVAILABLE = False

# 데이터베이스
DB_PATH = Path("/sdcard/Download/game_logs.db")

class GameDatabase:
    """게임 로그 저장소"""
    
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        """데이터베이스 초기화"""
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
        """게임 세션 저장"""
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
        """예측 저장"""
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
    """색상 기반 게임 분석"""
    
    def __init__(self):
        self.db = GameDatabase()
        
        # 색상 범위 정의 (HSV)
        self.rabbit_lower = np.array([85, 50, 50])
        self.rabbit_upper = np.array([130, 255, 255])
        
        self.pig_lower1 = np.array([0, 50, 50])
        self.pig_upper1 = np.array([25, 255, 255])
        
        self.pig_lower2 = np.array([130, 50, 50])
        self.pig_upper2 = np.array([180, 255, 255])
        
        self.bright_lower = np.array([0, 0, 200])
        self.bright_upper = np.array([180, 100, 255])
    
    def detect_job_state(self, frame):
        """하단 도구모음에서 직업 상태 감지"""
        if frame is None:
            return "대기", None
        
        height = frame.shape[0]
        
        # 하단 영역
        toolbar_top = int(height * 0.85)
        toolbar = frame[toolbar_top:, :]
        
        hsv = cv2.cvtColor(toolbar, cv2.COLOR_RGB2HSV)
        
        rabbit_mask = cv2.inRange(hsv, self.rabbit_lower, self.rabbit_upper)
        pig_mask1 = cv2.inRange(hsv, self.pig_lower1, self.pig_upper1)
        pig_mask2 = cv2.inRange(hsv, self.pig_lower2, self.pig_upper2)
        pig_mask = cv2.bitwise_or(pig_mask1, pig_mask2)
        
        rabbit_count = cv2.countNonZero(rabbit_mask)
        pig_count = cv2.countNonZero(pig_mask)
        
        gray_hsv = hsv.copy()
        gray_mask = cv2.inRange(gray_hsv, (0, 0, 100), (180, 50, 200))
        gray_count = cv2.countNonZero(gray_mask)
        
        threshold = 1000
        
        if gray_count > rabbit_count and gray_count > pig_count:
            return "대기", None
        elif rabbit_count > threshold and rabbit_count > pig_count:
            return "토끼", rabbit_mask
        elif pig_count > threshold and pig_count > rabbit_count:
            return "돼지", pig_mask
        
        return "대기", None
    
    def detect_button_positions(self, frame):
        """하단 버튼 위치 감지"""
        if frame is None:
            return []
        
        height = frame.shape[0]
        
        button_top = int(height * 0.75)
        button_area = frame[button_top:int(height * 0.95), :]
        
        hsv = cv2.cvtColor(button_area, cv2.COLOR_RGB2HSV)
        
        rabbit_mask = cv2.inRange(hsv, self.rabbit_lower, self.rabbit_upper)
        pig_mask1 = cv2.inRange(hsv, self.pig_lower1, self.pig_upper1)
        pig_mask2 = cv2.inRange(hsv, self.pig_lower2, self.pig_upper2)
        
        contours_rabbit = cv2.findContours(rabbit_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        contours_pig1 = cv2.findContours(pig_mask1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        contours_pig2 = cv2.findContours(pig_mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        
        buttons = []
        
        for contour in contours_rabbit:
            area = cv2.contourArea(contour)
            if 2000 < area < 50000:
                x, y, w, h = cv2.boundingRect(contour)
                buttons.append({
                    'pos': (x + button_top, y, w, h),
                    'job': '토끼',
                    'center_x': x + w // 2
                })
        
        for contour in contours_pig1 + contours_pig2:
            area = cv2.contourArea(contour)
            if 2000 < area < 50000:
                x, y, w, h = cv2.boundingRect(contour)
                buttons.append({
                    'pos': (x + button_top, y, w, h),
                    'job': '돼지',
                    'center_x': x + w // 2
                })
        
        buttons.sort(key=lambda b: b['center_x'])
        
        return buttons
    
    def detect_top_pattern(self, frame):
        """상단 패턴 분석"""
        if frame is None:
            return "없음"
        
        height = frame.shape[0]
        top_area = frame[:int(height * 0.2), :]
        
        hsv = cv2.cvtColor(top_area, cv2.COLOR_RGB2HSV)
        bright_mask = cv2.inRange(hsv, self.bright_lower, self.bright_upper)
        
        contours = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        
        pattern_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 20000:
                pattern_count += 1
        
        return f"패턴({pattern_count})" if pattern_count > 0 else "없음"
    
    def decide_button(self, job_state, pattern, available_buttons):
        """버튼 선택 결정"""
        if job_state == "대기" or not available_buttons:
            return None, None
        
        matching_buttons = [b for b in available_buttons if b['job'] == job_state]
        
        if matching_buttons:
            return matching_buttons[0], matching_buttons[0]['job']
        
        return None, None


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
        
        # 컴팩트 상태 (아이콘)
        self.btn_expand = Button(
            text='⊕',
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'right': 1, 'top': 1}
        )
        self.btn_expand.bind(on_press=self.expand)
        self.add_widget(self.btn_expand)
    
    def expand(self, instance):
        """확장"""
        if not self.is_expanded:
            self.is_expanded = True
            self.clear_widgets()
            self.create_expanded_ui()
    
    def create_expanded_ui(self):
        """확장 UI"""
        # 메인 박스
        main_box = BoxLayout(orientation='vertical', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        
        # 상단 바
        top_bar = BoxLayout(size_hint_y=0.1, padding=5, spacing=5)
        top_bar.add_widget(Label(text='🎮 떡치기', size_hint_x=0.7))
        
        btn_min = Button(text='_', size_hint_x=0.15)
        btn_min.bind(on_press=self.minimize)
        top_bar.add_widget(btn_min)
        
        btn_close = Button(text='✕', size_hint_x=0.15)
        btn_close.bind(on_press=self.close)
        top_bar.add_widget(btn_close)
        
        main_box.add_widget(top_bar)
        
        # 정보 영역
        info_box = BoxLayout(orientation='vertical', size_hint_y=0.6, padding=10, spacing=5)
        
        self.label_status = Label(text='상태: 대기', size_hint_y=0.2)
        info_box.add_widget(self.label_status)
        
        self.label_button = Label(text='다음 버튼: -', size_hint_y=0.2)
        info_box.add_widget(self.label_button)
        
        self.label_stats = Label(text='라운드: 0 | 성공: 0', size_hint_y=0.2)
        info_box.add_widget(self.label_stats)
        
        main_box.add_widget(info_box)
        
        # 제어 버튼
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
        """축소"""
        if self.is_expanded:
            self.is_expanded = False
            self.clear_widgets()
            self.btn_expand = Button(
                text='⊕',
                size_hint=(None, None),
                size=(60, 60),
                pos_hint={'right': 1, 'top': 1}
            )
            self.btn_expand.bind(on_press=self.expand)
            self.add_widget(self.btn_expand)
    
    def close(self, instance):
        """닫기"""
        if self.running:
            self.stop_game(None)
        self.parent.remove_widget(self)
    
    def start_game(self, instance):
        """게임 시작"""
        self.running = True
        self.btn_start.disabled = True
        self.round_count = 0
        self.success_count = 0
        self.session_id = self.analyzer.db.save_session(0, 0, 0)
        
        thread = threading.Thread(target=self.game_loop, daemon=True)
        thread.start()
    
    def stop_game(self, instance):
        """게임 정지"""
        self.running = False
        self.btn_start.disabled = False
    
    def game_loop(self):
        """게임 루프"""
        last_update = time.time()
        
        while self.running:
            start_time = time.time()
            
            try:
                # 화면 캡처 (실제로는 접근성 서비스나 screencap 사용)
                # 테스트용으로는 None 반환
                frame = self.capture_screen()
                
                if frame is not None:
                    job_state, _ = self.analyzer.detect_job_state(frame)
                    
                    if job_state != "대기":
                        pattern = self.analyzer.detect_top_pattern(frame)
                        buttons = self.analyzer.detect_button_positions(frame)
                        
                        button, button_job = self.analyzer.decide_button(job_state, pattern, buttons)
                        
                        button_color_map = {
                            '토끼': '청/초/파',
                            '돼지': '빨/주/노/핑/보'
                        }
                        button_color = button_color_map.get(button_job, '-')
                        
                        if time.time() - last_update > 0.1:
                            Clock.schedule_once(
                                lambda dt: self.update_ui(job_state, button_color, f"패턴({len(buttons)})"),
                                0
                            )
                            last_update = time.time()
                        
                        if button:
                            self.click_button(button)
                            self.success_count += 1
                            self.round_count += 1
                            
                            self.analyzer.db.save_prediction(
                                self.session_id, job_state, f"패턴({len(buttons)})",
                                button_color, "성공"
                            )
                    else:
                        if time.time() - last_update > 0.1:
                            Clock.schedule_once(
                                lambda dt: self.update_ui("대기", "-", "-"),
                                0
                            )
                            last_update = time.time()
                
                elapsed = time.time() - start_time
                sleep_time = max(0.01 - elapsed, 0)
                time.sleep(sleep_time)
            
            except Exception as e:
                print(f"게임 루프 오류: {e}")
                self.running = False
    
    def capture_screen(self):
        """화면 캡처"""
        # Android에서 실제 구현 필요
        # 임시로 None 반환 (테스트용)
        return None
    
    def click_button(self, button):
        """버튼 클릭"""
        # Android 접근성 서비스 사용
        # 임시로 패스
        pass
    
    def update_ui(self, state, button_color, pattern):
        """UI 업데이트"""
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
                Permission.CAMERA,
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])
        
        self.analyzer = ColorAnalyzer()
        
        # 메인 레이아웃
        main_layout = FloatLayout()
        
        # 배경 (메인 윈도우)
        bg_box = BoxLayout(orientation='vertical', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        
        title = Label(
            text='🎮 마피아42 떡치기 자동 플레이',
            size_hint_y=0.2,
            font_size='18sp'
        )
        bg_box.add_widget(title)
        
        desc = Label(
            text='아래 버튼을 클릭하면 플로팅 팝업이 나타납니다',
            size_hint_y=0.1,
            font_size='12sp'
        )
        bg_box.add_widget(desc)
        
        btn_start = Button(
            text='▶ 시작',
            size_hint_y=0.2,
            size_hint_x=0.6,
            pos_hint={'center_x': 0.5}
        )
        btn_start.bind(on_press=self.show_popup)
        bg_box.add_widget(btn_start)
        
        # 빈 공간
        bg_box.add_widget(Label(size_hint_y=0.5))
        
        main_layout.add_widget(bg_box)
        
        return main_layout
    
    def show_popup(self, instance):
        """플로팅 팝업 표시"""
        popup = FloatingPopup(self.analyzer, size_hint=(0.5, 0.5), pos_hint={'right': 1, 'top': 1})
        self.root.add_widget(popup)


if __name__ == '__main__':
    Mafia42App().run()
