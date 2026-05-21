import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys


def find_ffmpeg():
    """嘗試找到 ffmpeg 可執行檔路徑"""
    candidates = ["ffmpeg", "ffmpeg.exe"]
    for c in candidates:
        try:
            result = subprocess.run([c, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


FFMPEG = find_ffmpeg()


class LogPane(scrolledtext.ScrolledText):
    def __init__(self, master, **kwargs):
        super().__init__(master, state="disabled", wrap="word", height=10, **kwargs)

    def append(self, text):
        self.configure(state="normal")
        self.insert("end", text)
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


class FixVideoTab(ttk.Frame):
    """修正影片：轉檔 + 縮放"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()

    def _build(self):
        pad = {"padx": 6, "pady": 4}

        # 輸入檔案
        ttk.Label(self, text="輸入影片：").grid(row=0, column=0, sticky="w", **pad)
        self.input_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.input_var, width=48).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(self, text="瀏覽…", command=self._pick_input).grid(row=0, column=2, **pad)

        # 輸出檔案
        ttk.Label(self, text="輸出檔案：").grid(row=1, column=0, sticky="w", **pad)
        self.output_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.output_var, width=48).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(self, text="瀏覽…", command=self._pick_output).grid(row=1, column=2, **pad)

        # 參數
        param_frame = ttk.LabelFrame(self, text="參數", padding=8)
        param_frame.grid(row=2, column=0, columnspan=3, sticky="ew", **pad)

        ttk.Label(param_frame, text="解析度寬：").grid(row=0, column=0, sticky="w", padx=4)
        self.width_var = tk.StringVar(value="1080")
        ttk.Entry(param_frame, textvariable=self.width_var, width=8).grid(row=0, column=1, padx=4)

        ttk.Label(param_frame, text="解析度高：").grid(row=0, column=2, sticky="w", padx=12)
        self.height_var = tk.StringVar(value="1920")
        ttk.Entry(param_frame, textvariable=self.height_var, width=8).grid(row=0, column=3, padx=4)

        ttk.Label(param_frame, text="CRF 品質（0=最佳，51=最差）：").grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=6)
        self.crf_var = tk.IntVar(value=18)
        crf_scale = ttk.Scale(param_frame, from_=0, to=51, orient="horizontal",
                              variable=self.crf_var, length=200,
                              command=lambda v: self.crf_label.config(text=str(int(float(v)))))
        crf_scale.grid(row=1, column=2, columnspan=2, padx=4)
        self.crf_label = ttk.Label(param_frame, text="18", width=3)
        self.crf_label.grid(row=1, column=4, padx=4)

        # 執行按鈕
        self.run_btn = ttk.Button(self, text="▶  開始轉換", command=self._run)
        self.run_btn.grid(row=3, column=0, columnspan=3, pady=8)

        # 日誌
        ttk.Label(self, text="執行記錄：").grid(row=4, column=0, sticky="w", **pad)
        self.log = LogPane(self)
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", **pad)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)

    def _pick_input(self):
        path = filedialog.askopenfilename(
            title="選擇輸入影片",
            filetypes=[("影片檔案", "*.mp4 *.mov *.mkv *.avi"), ("所有檔案", "*.*")]
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                base, ext = os.path.splitext(path)
                self.output_var.set(f"{base}_fixed{ext}")

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="選擇輸出路徑",
            defaultextension=".mp4",
            filetypes=[("MP4 影片", "*.mp4"), ("所有檔案", "*.*")]
        )
        if path:
            self.output_var.set(path)

    def _run(self):
        inp = self.input_var.get().strip()
        out = self.output_var.get().strip()
        if not inp or not out:
            messagebox.showwarning("缺少資訊", "請填寫輸入和輸出檔案路徑。")
            return
        if not os.path.isfile(inp):
            messagebox.showerror("檔案不存在", f"找不到輸入檔案：\n{inp}")
            return
        if not FFMPEG:
            messagebox.showerror("找不到 FFmpeg", "請先安裝 FFmpeg 並確認其在系統 PATH 中。")
            return

        w = self.width_var.get().strip()
        h = self.height_var.get().strip()
        crf = self.crf_var.get()

        cmd = [
            FFMPEG, "-y", "-i", inp,
            "-c:v", "libx264",
            "-crf", str(crf),
            "-vf", f"scale={w}:{h}",
            "-c:a", "copy",
            out
        ]

        self.log.clear()
        self.log.append(f"執行指令：{' '.join(cmd)}\n\n")
        self.run_btn.configure(state="disabled")
        threading.Thread(target=self._execute, args=(cmd,), daemon=True).start()

    def _execute(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            for line in proc.stdout:
                self.log.append(line)
            proc.wait()
            if proc.returncode == 0:
                self.log.append("\n✅ 轉換完成！\n")
            else:
                self.log.append(f"\n❌ 轉換失敗（代碼 {proc.returncode}）\n")
        except Exception as e:
            self.log.append(f"\n錯誤：{e}\n")
        finally:
            self.run_btn.configure(state="normal")


class AddBgmTab(ttk.Frame):
    """加入背景音樂"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()

    def _build(self):
        pad = {"padx": 6, "pady": 4}

        # 輸入影片
        ttk.Label(self, text="輸入影片：").grid(row=0, column=0, sticky="w", **pad)
        self.video_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.video_var, width=48).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(self, text="瀏覽…", command=self._pick_video).grid(row=0, column=2, **pad)

        # 背景音樂
        ttk.Label(self, text="背景音樂：").grid(row=1, column=0, sticky="w", **pad)
        self.audio_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.audio_var, width=48).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(self, text="瀏覽…", command=self._pick_audio).grid(row=1, column=2, **pad)

        # 輸出檔案
        ttk.Label(self, text="輸出檔案：").grid(row=2, column=0, sticky="w", **pad)
        self.output_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.output_var, width=48).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Button(self, text="瀏覽…", command=self._pick_output).grid(row=2, column=2, **pad)

        # 參數
        param_frame = ttk.LabelFrame(self, text="參數", padding=8)
        param_frame.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)

        ttk.Label(param_frame, text="背景音樂音量（0.0 ~ 2.0）：").grid(row=0, column=0, sticky="w", padx=4)
        self.vol_var = tk.DoubleVar(value=0.3)
        vol_scale = ttk.Scale(param_frame, from_=0.0, to=2.0, orient="horizontal",
                              variable=self.vol_var, length=200,
                              command=lambda v: self.vol_label.config(text=f"{float(v):.2f}"))
        vol_scale.grid(row=0, column=1, padx=4)
        self.vol_label = ttk.Label(param_frame, text="0.30", width=5)
        self.vol_label.grid(row=0, column=2, padx=4)

        # 執行按鈕
        self.run_btn = ttk.Button(self, text="▶  開始混音", command=self._run)
        self.run_btn.grid(row=4, column=0, columnspan=3, pady=8)

        # 日誌
        ttk.Label(self, text="執行記錄：").grid(row=5, column=0, sticky="w", **pad)
        self.log = LogPane(self)
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", **pad)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(6, weight=1)

    def _pick_video(self):
        path = filedialog.askopenfilename(
            title="選擇輸入影片",
            filetypes=[("影片檔案", "*.mp4 *.mov *.mkv *.avi"), ("所有檔案", "*.*")]
        )
        if path:
            self.video_var.set(path)
            if not self.output_var.get():
                base, ext = os.path.splitext(path)
                self.output_var.set(f"{base}_bgm{ext}")

    def _pick_audio(self):
        path = filedialog.askopenfilename(
            title="選擇背景音樂",
            filetypes=[("音訊檔案", "*.mp3 *.wav *.aac *.flac *.m4a"), ("所有檔案", "*.*")]
        )
        if path:
            self.audio_var.set(path)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="選擇輸出路徑",
            defaultextension=".mp4",
            filetypes=[("MP4 影片", "*.mp4"), ("所有檔案", "*.*")]
        )
        if path:
            self.output_var.set(path)

    def _run(self):
        video = self.video_var.get().strip()
        audio = self.audio_var.get().strip()
        out = self.output_var.get().strip()

        if not video or not audio or not out:
            messagebox.showwarning("缺少資訊", "請填寫影片、音樂和輸出檔案路徑。")
            return
        if not os.path.isfile(video):
            messagebox.showerror("檔案不存在", f"找不到影片：\n{video}")
            return
        if not os.path.isfile(audio):
            messagebox.showerror("檔案不存在", f"找不到音樂：\n{audio}")
            return
        if not FFMPEG:
            messagebox.showerror("找不到 FFmpeg", "請先安裝 FFmpeg 並確認其在系統 PATH 中。")
            return

        vol = f"{self.vol_var.get():.2f}"
        filter_complex = f"[1:a]volume={vol}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]"

        cmd = [
            FFMPEG, "-y",
            "-i", video,
            "-i", audio,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            out
        ]

        self.log.clear()
        self.log.append(f"執行指令：{' '.join(cmd)}\n\n")
        self.run_btn.configure(state="disabled")
        threading.Thread(target=self._execute, args=(cmd,), daemon=True).start()

    def _execute(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            for line in proc.stdout:
                self.log.append(line)
            proc.wait()
            if proc.returncode == 0:
                self.log.append("\n✅ 混音完成！\n")
            else:
                self.log.append(f"\n❌ 混音失敗（代碼 {proc.returncode}）\n")
        except Exception as e:
            self.log.append(f"\n錯誤：{e}\n")
        finally:
            self.run_btn.configure(state="normal")


def main():
    root = tk.Tk()
    root.title("FFmpeg 工具箱")
    root.minsize(640, 520)
    root.resizable(True, True)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    tab1 = FixVideoTab(notebook)
    notebook.add(tab1, text="  修正影片（縮放 + 重新編碼）  ")

    tab2 = AddBgmTab(notebook)
    notebook.add(tab2, text="  加入背景音樂  ")

    if not FFMPEG:
        status = ttk.Label(root, text="⚠️  找不到 FFmpeg，請安裝後重啟程式",
                           foreground="red", anchor="center")
        status.pack(fill="x", padx=8, pady=(0, 6))

    root.mainloop()


if __name__ == "__main__":
    main()
