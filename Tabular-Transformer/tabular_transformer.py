import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

import threading
import traceback
import time
import pandas as pd
import numpy as np
import datetime
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from anonymize.semantics import guess_semantic_field
from anonymize.transforms import transform_series

from policy.policy_low import policy_low
from policy.policy_high import policy_high

def _guess_ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()

def _promote_first_row_header(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols = list(df.columns)
    unnamed_ratio = sum([str(c).startswith("Unnamed") for c in cols]) / max(1, len(cols))
    if unnamed_ratio >= 0.5:
        new_header = df.iloc[0].astype(str).tolist()
        df2 = df.iloc[1:].copy()
        df2.columns = new_header
        df2.reset_index(drop=True, inplace=True)
        return df2
    return df

def load_structured(path: str) -> pd.DataFrame:
    ext = _guess_ext(path)
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"지원하지 않는 입력 형식입니다: {ext} (csv/xlsx/xls만 가능)")
    return _promote_first_row_header(df)

def save_structured(df: pd.DataFrame, path: str) -> None:
    ext = _guess_ext(path)
    if ext == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif ext in [".xlsx", ".xls"]:
        df.to_excel(path, index=False)
    else:
        fallback = path + ".csv"
        df.to_csv(fallback, index=False, encoding="utf-8-sig")
        raise ValueError(f"알 수 없는 출력 확장자라서 CSV로 저장했습니다: {fallback}")

def build_output_path(input_path: str, output_dir: str) -> str:
    base = os.path.basename(input_path)
    stem, ext = os.path.splitext(base)
    out_name = f"{stem}_anonymized{ext}"
    if output_dir.strip() == "":
        return os.path.join(os.path.dirname(input_path), out_name)
    return os.path.join(output_dir, out_name)

def build_log_path(out_path: str) -> str:
    stem, _ = os.path.splitext(out_path)
    return stem + "_log.json"


def force_series_1d(obj) -> pd.Series:
    if isinstance(obj, pd.Series):
        s = obj.copy()
    else:
        try:
            s = pd.Series(list(obj))
        except Exception:
            s = pd.Series([obj])

    def _squash_cell(v):
        if isinstance(v, (list, tuple, np.ndarray, dict)):
            return str(v)
        return v

    s = s.map(_squash_cell).reset_index(drop=True)
    return s

class TransformGUI:
    def __init__(self, master):
        self.master = master
        master.title("정형 데이터 익명화 변환기 (멀티 파일)")
        master.resizable(False, False)

        # UI Vars
        self.input_paths_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="low")
        self.allow_dx_var = tk.BooleanVar(value=False)

        self._selected_inputs: List[str] = []
        self._job_error_msg: Optional[str] = None
        self._job_error_trace: Optional[str] = None

        frame_input = tk.Frame(master)
        frame_input.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_input, text="원본 파일(여러 개 선택 가능) (CSV / Excel)").pack(anchor="w")
        row_input = tk.Frame(frame_input)
        row_input.pack(fill="x")

        self.input_entry = tk.Entry(row_input, textvariable=self.input_paths_var, width=50)
        self.input_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row_input, text="찾기...", command=self.browse_inputs).pack(side="left", padx=5)

        frame_output = tk.Frame(master)
        frame_output.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_output, text="출력 폴더 (비우면 원본 파일 폴더에 저장)").pack(anchor="w")
        row_output = tk.Frame(frame_output)
        row_output.pack(fill="x")

        self.output_entry = tk.Entry(row_output, textvariable=self.output_dir_var, width=50)
        self.output_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row_output, text="폴더 선택...", command=self.browse_output_dir).pack(side="left", padx=5)

        frame_mode = tk.LabelFrame(master, text="익명화 강도 선택", padx=5, pady=5)
        frame_mode.pack(fill="x", padx=10, pady=10)

        tk.Radiobutton(frame_mode, text="저수준 익명화", variable=self.mode_var, value="low",
                       command=self.update_dx_policy_label).pack(anchor="w")
        tk.Radiobutton(frame_mode, text="고수준 익명화", variable=self.mode_var, value="high",
                       command=self.update_dx_policy_label).pack(anchor="w")

        frame_dx = tk.LabelFrame(master, text="진단명/코드 옵션", padx=5, pady=5)
        frame_dx.pack(fill="x", padx=10, pady=10)

        self.dx_check = tk.Checkbutton(
            frame_dx,
            text="진단명 / 진단코드 포함 (허가받았을 때만 체크)",
            variable=self.allow_dx_var,
            command=self.update_dx_policy_label
        )
        self.dx_check.pack(anchor="w")

        self.dx_policy_label = tk.Label(frame_dx, text="", fg="#aa0000",
                                        wraplength=520, justify="left")
        self.dx_policy_label.pack(fill="x", pady=(4, 0))

        frame_run = tk.Frame(master)
        frame_run.pack(fill="x", padx=10, pady=10)

        self.run_button = tk.Button(
            frame_run,
            text="익명화 실행 (선택된 파일 모두)",
            command=self.run_clicked,
            bg="#4CAF50", fg="white"
        )
        self.run_button.pack(fill="x")

        self.banner_label = tk.Label(master, text="대기 중", bg="#dddddd", fg="#222",
                                     anchor="center", padx=6, pady=6)
        self.banner_label.pack(fill="x", padx=10, pady=(6, 4))

        self.progress = ttk.Progressbar(master, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=10)

        info_frame = tk.Frame(master)
        info_frame.pack(fill="x", padx=10, pady=(6, 6))

        self.file_label = tk.Label(info_frame, text="처리 중 파일: -", fg="#444", anchor="w")
        self.file_label.pack(fill="x")

        self.field_label = tk.Label(info_frame, text="처리 중 필드: -", fg="#444", anchor="w")
        self.field_label.pack(fill="x")

        self.eta_label = tk.Label(info_frame, text="예상 남은 시간: -", fg="#888", anchor="w")
        self.eta_label.pack(fill="x")

        self.status_label = tk.Label(master, text="", fg="#444", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 8))

        frame_log = tk.LabelFrame(master, text="실시간 로그", padx=5, pady=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        log_inner = tk.Frame(frame_log)
        log_inner.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_inner,
            height=15,
            wrap="none",
            state="disabled",
            bg="#111", fg="#eee"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = tk.Scrollbar(log_inner, command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scroll.set)

        self.update_dx_policy_label()

        self._job_error_msg = None
        self._job_error_trace = None

    def append_log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.master.update_idletasks()

    def _set_banner(self, text: str):
        self.banner_label.config(text=text)
        self.master.update_idletasks()

    def _set_progress(self, pct: float):
        self.progress["value"] = max(0.0, min(100.0, pct))
        self.master.update_idletasks()

    def _set_file_field_eta(self, file_text: str, field_text: str, eta_text: str):
        self.file_label.config(text=file_text)
        self.field_label.config(text=field_text)
        self.eta_label.config(text=eta_text)
        self.master.update_idletasks()

    def _format_eta(self, eta_sec: Optional[float]) -> str:
        if eta_sec is None:
            return "예상 남은 시간: 계산 중..."
        if eta_sec < 0:
            return "예상 남은 시간: -"
        mm = int(eta_sec // 60)
        ss = int(eta_sec % 60)
        return f"예상 남은 시간: 약 {mm:02d}:{ss:02d}"

    def set_busy(self, busy: bool):
        if busy:
            self.run_button.config(state="disabled", text="처리 중...", bg="#888888")
        else:
            self.run_button.config(state="normal", text="익명화 실행 (선택된 파일 모두)", bg="#4CAF50")

    def update_dx_policy_label(self):
        mode = self.mode_var.get()
        allow_dx = self.allow_dx_var.get()

        if mode == "high" and allow_dx:
            txt = "고수준 익명화 + 진단정보 포함: 옵션이 적절한지 확인해주세요"
            color = "#ff0000"
        elif mode == "high" and not allow_dx:
            txt = "고수준 익명화: 진단명/코드는 제거됩니다."
            color = "#aa0000"
        elif mode == "low" and allow_dx:
            txt = "저수준 익명화: 진단명/코드가 포함됩니다."
            color = "#cc6600"
        else:
            txt = "저수준 익명화: 진단명/코드는 제거됩니다."
            color = "#aa0000"

        self.dx_policy_label.config(text=txt, fg=color)

    def _reset_job_state(self):
        self._job_error_msg = None
        self._job_error_trace = None
        self.status_label.config(text="")
        self._set_banner("처리 준비 중...")
        self._set_progress(0)
        self._set_file_field_eta("처리 중 파일: -", "처리 중 필드: -", "예상 남은 시간: -")

    def browse_inputs(self):
        paths = filedialog.askopenfilenames(
            title="원본 데이터 선택 (여러 개 선택 가능)",
            filetypes=[
                ("Data files", "*.csv *.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*"),
            ]
        )
        if not paths:
            return
        self._selected_inputs = list(paths)

        if len(self._selected_inputs) <= 3:
            shown = " | ".join(self._selected_inputs)
        else:
            shown = f"{self._selected_inputs[0]} | {self._selected_inputs[1]} | ... (총 {len(self._selected_inputs)}개)"
        self.input_paths_var.set(shown)

        self.append_log(f"입력 파일 {len(self._selected_inputs)}개 선택됨.")

    def browse_output_dir(self):
        d = filedialog.askdirectory(title="출력 폴더 선택")
        if d:
            self.output_dir_var.set(d)

    def run_clicked(self):
        if not self._selected_inputs:
            messagebox.showerror("오류", "원본 파일을 1개 이상 선택하세요.")
            return

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self._reset_job_state()
        self.set_busy(True)

        worker = threading.Thread(target=self._job_multi, daemon=True)
        worker.start()

    def _job_multi(self):
        try:
            mode = self.mode_var.get()
            allow_dx = self.allow_dx_var.get()
            policy = policy_high if mode == "high" else policy_low

            output_dir = self.output_dir_var.get().strip()
            n_files = len(self._selected_inputs)

            total_cols_all = 0
            per_file_cols = {}
            for p in self._selected_inputs:
                try:
                    df_tmp = load_structured(p)
                    per_file_cols[p] = len(df_tmp.columns)
                    total_cols_all += len(df_tmp.columns)
                except Exception as e:
                    per_file_cols[p] = 0
                    self.master.after(0, lambda m=f"[SKIP] 파일 로드 실패: {p} ({e})": self.append_log(m))

            if total_cols_all == 0:
                raise RuntimeError("처리 가능한 컬럼이 없습니다. (모든 파일 로드 실패 또는 빈 파일)")

            completed_cols = 0
            t_global = time.time()

            for file_idx, input_path in enumerate(self._selected_inputs, start=1):
                n_cols = per_file_cols.get(input_path, 0)
                if n_cols <= 0:
                    continue

                df_orig = load_structured(input_path)
                cols = list(df_orig.columns)

                self.master.after(0, lambda p=input_path, i=file_idx, nf=n_files: self.append_log(
                    f"=== [{i}/{nf}] 익명화 시작: {p} (cols={len(cols)}) ==="
                ))

                out_cols: Dict[str, pd.Series] = {}
                log_info: Dict[str, Dict[str, Any]] = {}

                for col_idx, c in enumerate(cols, start=1):
                    col_series = df_orig[c]
                    sem = guess_semantic_field(c, col_series)
                    action = policy.get(sem, "keep")

                    try:
                        new_series = transform_series(
                            col_series,
                            action,
                            diagnosis_allowed=allow_dx,
                            semantic=sem,
                        )
                    except Exception as e:
                        err_msg = f"[transform_series ERROR] file={os.path.basename(input_path)} col={c} sem={sem} action={action} err={e}"
                        self.master.after(0, lambda m=err_msg: self.append_log(m))
                        traceback.print_exc()
                        new_series = pd.Series([""] * len(col_series))

                    if isinstance(new_series, pd.DataFrame):
                        sub_df = new_series
                        warn_msg = f"[WARN] file={os.path.basename(input_path)} '{c}' -> DataFrame({sub_df.shape}), 여러 컬럼 분해"
                        self.master.after(0, lambda m=warn_msg: self.append_log(m))
                        for subcol in sub_df.columns:
                            safe_key = f"{c}_{subcol}"
                            out_cols[safe_key] = force_series_1d(sub_df[subcol])
                            log_info[safe_key] = {"semantic": sem, "action": action, "source": c}
                    else:
                        out_cols[c] = force_series_1d(new_series)
                        log_info[c] = {"semantic": sem, "action": action}

                    completed_cols += 1
                    elapsed = time.time() - t_global
                    avg_per_col = elapsed / max(1, completed_cols)
                    remain_cols = total_cols_all - completed_cols
                    eta_sec = avg_per_col * remain_cols if remain_cols > 0 else 0.0
                    pct = (completed_cols / total_cols_all) * 100.0

                    banner = "처리 중..."
                    file_text = f"처리 중 파일: {os.path.basename(input_path)} ({file_idx}/{n_files})"
                    field_text = f"처리 중 필드: {c} ({col_idx}/{len(cols)})"
                    eta_text = self._format_eta(eta_sec)

                    self.master.after(0, lambda b=banner: self._set_banner(b))
                    self.master.after(0, lambda pc=pct: self._set_progress(pc))
                    self.master.after(0, lambda ft=file_text, fld=field_text, et=eta_text: self._set_file_field_eta(ft, fld, et))
                    self.master.after(0, lambda m=f"{file_idx}/{n_files} | 남은~{eta_sec:.2f}s ({pct:.1f}%) | {c}": self.append_log(m))

                anon_df = pd.DataFrame(out_cols)

                out_path = build_output_path(input_path, output_dir)
                save_structured(anon_df, out_path)

                log_path = build_log_path(out_path)
                payload = {
                    "_meta": {
                        "mode": mode,
                        "allow_dx": bool(allow_dx),
                        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                        "source_file": os.path.basename(input_path),
                        "output_file": os.path.basename(out_path),
                    },
                    "log_info": log_info
                }
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                self.master.after(0, lambda op=out_path: self.append_log(f"익명화 저장 완료: {op}"))
                self.master.after(0, lambda lp=log_path: self.append_log(f"log 저장 완료: {lp}"))

        except Exception as e:
            self._job_error_msg = str(e)
            self._job_error_trace = traceback.format_exc()
        finally:
            self.master.after(0, self._finish_ui)

    def _finish_ui(self):
        self.set_busy(False)

        if self._job_error_msg:
            self._set_banner("익명화 실패")
            self.status_label.config(text="익명화 실패 (하단 로그 확인)")
            messagebox.showerror("익명화 실패", f"{self._job_error_msg}\n\n하단 로그를 확인하세요.")
            self.append_log("[ERROR] " + self._job_error_msg)
            if self._job_error_trace:
                for line in self._job_error_trace.splitlines():
                    self.append_log(line)
            return

        self._set_banner("익명화 완료")
        self._set_progress(100)
        self.status_label.config(text=f"익명화 완료")
        messagebox.showinfo("익명화 완료", "익명화가 완료되었습니다.\n(익명화 파일 + *_anonymized_log.json 생성됨)")
        self.append_log("=== 익명화 작업 완료 ===")


def launch():
    logging.basicConfig(level=logging.ERROR)
    root = tk.Tk()
    app = TransformGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
