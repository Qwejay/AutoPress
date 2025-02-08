import threading
import time
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard
from pynput.keyboard import Key, Controller, Listener
import pystray
from PIL import Image, ImageDraw
from ttkthemes import ThemedTk

# 全局配置
DEFAULT_HOTKEY = Key.f6
DEFAULT_INTERVAL = 5.0

# 全局变量
running = False
keys_to_press = []
trigger_interval = DEFAULT_INTERVAL
start_stop_hotkey = DEFAULT_HOTKEY
controller = Controller()
hotkey_listener = None

# 特殊按键映射
SPECIAL_KEYS = {
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift,
    'enter': Key.enter, 'esc': Key.esc, 'space': Key.space
}

# GUI初始化
root = ThemedTk(theme="arc")
root.title("AutoPress 1.0")
root.geometry("350x400")
root.resizable(False, False)

# 状态栏
status_var = tk.StringVar(value="🛑 已停止")
status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, padding=4)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

class HotkeyManager:
    def __init__(self):
        self.current_hotkey = DEFAULT_HOTKEY
        self.listener = None
        self.listener_running = False

    def start_listener(self):
        def on_press(key):
            if key == self.current_hotkey:
                toggle_running()
        
        if not self.listener_running:
            self.listener = Listener(on_press=on_press)
            self.listener.start()
            self.listener_running = True

    def update_hotkey(self, new_hotkey):
        if self.listener:
            self.listener.stop()
        self.current_hotkey = new_hotkey
        self.start_listener()

hotkey_mgr = HotkeyManager()

# 系统托盘
class TrayManager:
    def __init__(self):
        self.icon = None
        self.menu = (
            pystray.MenuItem('打开主界面', self.show_app),
            pystray.MenuItem('开始/停止', self.toggle_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出', self.quit_app)
        )
        
    def create_icon(self):
        image = Image.new("RGB", (64, 64), "white")
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "AKM", fill="black")
        self.icon = pystray.Icon("auto_key", image, "AutoPress", self.menu)
        self.icon.run()

    def show_app(self, icon, item):
        root.deiconify()

    def toggle_running(self, icon, item):
        toggle_running()

    def quit_app(self, icon, item):
        self.icon.stop()
        root.destroy()

tray_icon = TrayManager()

# 核心功能
def toggle_running():
    global running
    running = not running
    if running:
        start()
    else:
        stop()

def start():
    if not keys_to_press:
        status_var.set("❌ 请先添加至少一个按键")
        toggle_running()
        return
    
    status_var.set("▶️ 运行中")
    start_btn.config(text="停止运行")
    tray_icon.icon.notify("自动按键已启动")

def stop():
    status_var.set("🛑 已停止")
    start_btn.config(text="开始运行")
    tray_icon.icon.notify("自动按键已停止")

def auto_press():
    while True:
        if running:
            for key in keys_to_press:
                if not running: break
                try:
                    controller.press(key)
                    controller.release(key)
                    time.sleep(trigger_interval)
                except Exception as e:
                    status_var.set(f"❌ 错误: {str(e)}")
        time.sleep(0.1)

# 快捷键设置功能
def set_hotkey():
    def on_press(key):
        try:
            key_str = key.char
        except AttributeError:
            key_str = key.name
        
        # 过滤无效按键
        if key_str in ['shift_r', 'shift_l', 'ctrl_r', 'ctrl_l']:
            return
        
        hotkey_mgr.update_hotkey(key)
        hotkey_label.config(text=f"当前快捷键: {key_str.capitalize()}")
        set_window.destroy()
        listener.stop()

    set_window = tk.Toplevel(root)
    set_window.title("设置快捷键")
    set_window.geometry("300x100")
    
    ttk.Label(set_window, text="请按下新的快捷键...", font=('Arial', 12)).pack(pady=20)
    listener = Listener(on_press=on_press)
    listener.start()

# 界面布局
def setup_gui():
    main_frame = ttk.Frame(root, padding=15)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 按键设置区
    key_frame = ttk.LabelFrame(main_frame, text="按键设置", padding=10)
    key_frame.grid(row=0, column=0, sticky="ew", pady=5)

    ttk.Label(key_frame, text="输入按键：").grid(row=0, column=0, padx=5)
    key_entry = ttk.Entry(key_frame, width=15)
    key_entry.grid(row=0, column=1, padx=5)

    def add_key():
        key_str = key_entry.get().strip().lower()
        if not key_str:
            return
        
        if key_str in SPECIAL_KEYS:
            key = SPECIAL_KEYS[key_str]
            display = key_str.upper()
        else:
            if len(key_str) != 1:
                status_var.set("❌ 只能输入单个字符或特殊按键名称")
                return
            key = key_str
            display = key_str.upper()
        
        keys_to_press.append(key)
        key_list.insert(tk.END, display)
        key_entry.delete(0, tk.END)
        status_var.set(f"✅ 已添加按键: {display}")

    ttk.Button(key_frame, text="添加", command=add_key, width=8).grid(row=0, column=2, padx=5)
    key_list = tk.Listbox(key_frame, height=3, width=20)
    key_list.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")

    # 参数设置区
    setting_frame = ttk.LabelFrame(main_frame, text="参数设置", padding=10)
    setting_frame.grid(row=1, column=0, sticky="ew", pady=10)

    ttk.Label(setting_frame, text="触发间隔（秒）：").grid(row=0, column=0)
    interval_entry = ttk.Entry(setting_frame, width=8)
    interval_entry.insert(0, str(DEFAULT_INTERVAL))
    interval_entry.grid(row=0, column=1, padx=5)

    def set_interval():
        try:
            global trigger_interval
            new_interval = float(interval_entry.get())
            if new_interval < 0.1:
                raise ValueError
            trigger_interval = new_interval
            status_var.set(f"✅ 间隔时间已设置为 {new_interval} 秒")
        except ValueError:
            status_var.set("❌ 请输入大于0.1的有效数字")

    ttk.Button(setting_frame, text="应用", command=set_interval, width=8).grid(row=0, column=2)

    # 快捷键设置
    hotkey_frame = ttk.Frame(setting_frame)
    hotkey_frame.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")
    ttk.Label(hotkey_frame, text="启停快捷键：").pack(side=tk.LEFT)
    global hotkey_label
    hotkey_label = ttk.Label(hotkey_frame, text="F6")
    hotkey_label.pack(side=tk.LEFT, padx=5)
    ttk.Button(hotkey_frame, text="更改", command=set_hotkey, width=8).pack(side=tk.LEFT)

    # 控制按钮
    global start_btn
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=2, column=0, pady=10)
    start_btn = ttk.Button(btn_frame, text="开始运行", command=toggle_running, width=12)
    start_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="最小化", command=root.withdraw).pack(side=tk.LEFT)

if __name__ == "__main__":
    hotkey_mgr.start_listener()
    threading.Thread(target=auto_press, daemon=True).start()
    threading.Thread(target=tray_icon.create_icon, daemon=True).start()
    setup_gui()
    root.mainloop()