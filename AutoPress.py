import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pynput.keyboard import Key, Controller, Listener
import pystray
from PIL import Image, ImageDraw
from ttkthemes import ThemedTk

# 全局配置常量
class Config:
    DEFAULT_HOTKEY = Key.f6
    DEFAULT_INTERVAL = 5.0
    MIN_INTERVAL = 0.1
    WINDOW_SIZE = "350x420"
    SPECIAL_KEYS = {
        'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
        'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
        'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift,
        'enter': Key.enter, 'esc': Key.esc, 'space': Key.space,
        'tab': Key.tab, 'backspace': Key.backspace, 'delete': Key.delete
    }

# 全局状态管理
class AppState:
    def __init__(self):
        self.running = False
        self.keys = []
        self.interval = Config.DEFAULT_INTERVAL
        self.hotkey = Config.DEFAULT_HOTKEY
        self.controller = Controller()
        self.lock = threading.Lock()

    def add_key(self, key):
        with self.lock:
            if key not in self.keys:
                self.keys.append(key)
                return True
        return False

    def remove_key(self, index):
        with self.lock:
            if 0 <= index < len(self.keys):
                del self.keys[index]
                return True
        return False

app_state = AppState()

# GUI初始化
root = ThemedTk(theme="arc")
root.title("AutoPress 2.0")
root.geometry(Config.WINDOW_SIZE)
root.resizable(False, False)

# 系统托盘管理
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
        draw.text((10, 10), "AP", fill="black")
        self.icon = pystray.Icon("auto_key", image, "AutoPress", self.menu)
        self.icon.run()

    def show_app(self, icon, item):
        root.after(0, root.deiconify)

    def toggle_running(self, icon, item):
        root.after(0, toggle_running)

    def quit_app(self, icon, item):
        root.after(0, self.cleanup)
        root.destroy()

    def cleanup(self):
        if self.icon:
            self.icon.stop()

tray_icon = TrayManager()

# 快捷键管理
class HotkeyManager:
    def __init__(self):
        self.current_hotkey = Config.DEFAULT_HOTKEY
        self.listener = None
        self.running = False

    def start(self):
        def on_press(key):
            if key == self.current_hotkey:
                root.after(0, toggle_running)
        
        if not self.running:
            self.listener = Listener(on_press=on_press)
            self.listener.start()
            self.running = True

    def update(self, new_hotkey):
        if self.listener:
            self.listener.stop()
        self.current_hotkey = new_hotkey
        self.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
        self.running = False

hotkey_mgr = HotkeyManager()

# 核心功能
def toggle_running():
    if not app_state.running:
        start()
    else:
        stop()

def start():
    if app_state.running:
        return

    if not app_state.keys:
        update_status("❌ 请先添加至少一个按键", error=True)
        return

    app_state.running = True
    update_ui_state()
    tray_icon.icon.notify("自动按键已启动")

def stop():
    app_state.running = False
    update_ui_state()
    tray_icon.icon.notify("自动按键已停止")

def auto_press():
    while True:
        if app_state.running:
            with app_state.lock:
                keys = app_state.keys.copy()
            
            for key in keys:
                if not app_state.running:
                    break
                try:
                    app_state.controller.press(key)
                    app_state.controller.release(key)
                    time.sleep(app_state.interval)
                except Exception as e:
                    handle_error(f"按键错误: {str(e)}")
        time.sleep(0.1)

# 界面辅助函数
def update_status(message, error=False):
    status_var.set(message)
    if error:
        root.bell()

def update_ui_state():
    if app_state.running:
        status_var.set("▶️ 运行中")
        start_btn.config(text="停止运行")
    else:
        status_var.set("🛑 已停止")
        start_btn.config(text="开始运行")
    key_list.selection_clear(0, tk.END)

def handle_error(message):
    update_status(f"❌ {message}", error=True)
    stop()

# 快捷键设置功能
def set_hotkey():
    def on_press(key):
        try:
            key_str = key.char
        except AttributeError:
            key_str = key.name

        if key_str.lower() in ['shift', 'ctrl', 'alt']:
            return

        hotkey_mgr.update(key)
        hotkey_label.config(text=f"当前快捷键: {key_str.capitalize()}")
        set_window.destroy()
        listener.stop()

    set_window = tk.Toplevel(root)
    set_window.title("设置快捷键")
    set_window.geometry("300x120")
    set_window.resizable(False, False)
    
    ttk.Label(set_window, text="请按下新的快捷键...", font=('Arial', 12)).pack(pady=25)
    listener = Listener(on_press=on_press)
    listener.start()

# GUI布局
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
            update_status("❌ 请输入有效按键", error=True)
            return
        
        key = Config.SPECIAL_KEYS.get(key_str, key_str)
        
        if isinstance(key, str) and len(key) != 1:
            update_status("❌ 无效按键格式", error=True)
            return
        
        if app_state.add_key(key):
            display = key_str.upper()
            key_list.insert(tk.END, display)
            key_entry.delete(0, tk.END)
            update_status(f"✅ 已添加按键: {display}")
        else:
            update_status("⚠️ 该按键已存在", error=True)

    def remove_key():
        selection = key_list.curselection()
        if selection:
            if app_state.remove_key(selection[0]):
                key_list.delete(selection[0])
                update_status("✅ 已移除选中按键")
            else:
                update_status("❌ 移除按键失败", error=True)
        else:
            update_status("❌ 请先选择要移除的按键", error=True)

    ttk.Button(key_frame, text="添加", command=add_key, width=8).grid(row=0, column=2, padx=5)
    ttk.Button(key_frame, text="移除", command=remove_key, width=8).grid(row=1, column=2, pady=5)
    
    global key_list
    key_list = tk.Listbox(key_frame, height=4, width=20, selectmode=tk.SINGLE)
    key_list.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

    # 参数设置区
    setting_frame = ttk.LabelFrame(main_frame, text="参数设置", padding=10)
    setting_frame.grid(row=1, column=0, sticky="ew", pady=10)

    ttk.Label(setting_frame, text="触发间隔（秒）：").grid(row=0, column=0)
    interval_entry = ttk.Entry(setting_frame, width=8)
    interval_entry.insert(0, str(Config.DEFAULT_INTERVAL))
    interval_entry.grid(row=0, column=1, padx=5)

    def set_interval():
        try:
            new_interval = float(interval_entry.get())
            if new_interval < Config.MIN_INTERVAL:
                raise ValueError
            app_state.interval = new_interval
            update_status(f"✅ 间隔时间已设置为 {new_interval} 秒")
        except ValueError:
            update_status(f"❌ 请输入大于{Config.MIN_INTERVAL}的有效数字", error=True)

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
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=2, column=0, pady=15, sticky="ew")

    global start_btn
    start_btn = ttk.Button(btn_frame, text="开始运行", command=toggle_running, width=12)
    start_btn.pack(side=tk.LEFT, padx=5)

    stop_btn = ttk.Button(btn_frame, text="强制停止", command=stop, width=12)
    stop_btn.pack(side=tk.LEFT, padx=5)

    ttk.Button(btn_frame, text="最小化", command=root.withdraw, width=8).pack(side=tk.RIGHT)

# 退出处理
def on_closing():
    if messagebox.askokcancel("退出", "确定要退出程序吗？"):
        stop()
        hotkey_mgr.stop()
        tray_icon.cleanup()
        root.destroy()

if __name__ == "__main__":
    root.protocol("WM_DELETE_WINDOW", on_closing)
    setup_gui()
    
    # 启动后台线程
    threading.Thread(target=auto_press, daemon=True).start()
    hotkey_mgr.start()
    threading.Thread(target=tray_icon.create_icon, daemon=True).start()
    
    # 状态初始化
    status_var = tk.StringVar(value="🛑 已停止")
    status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, padding=4)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()