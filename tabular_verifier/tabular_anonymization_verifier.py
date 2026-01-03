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

from tabular_application.validation_low import validate_low
from tabular_application.validation_high import validate_high
from tabular_application.validation_common import compute_validation_metrics

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

def save_csv(df: pd.DataFrame, path: str, append: bool = False) -> None:
    if append and os.path.exists(path):
        df.to_csv(path, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(path, index=False, encoding="utf-8-sig")

def _safe_str_series(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()

def _pick_qi_columns(df_anon: pd.DataFrame, log_info: Dict[str, Dict[str, Any]]) -> List[str]:
    qi_sem = {"age", "gender", "race", "ethnicity", "marital_status", "address", "zipcode", "visit_date"}
    cols = []
    for col in df_anon.columns:
        meta = log_info.get(col, {})
        sem = str(meta.get("semantic", "")).lower().strip()
        act = str(meta.get("action", "")).lower().strip()
        if sem in qi_sem and act != "drop":
            cols.append(col)
    return cols

def compute_k_group_sizes(df_anon: pd.DataFrame, qi_cols: List[str]) -> Tuple[Optional[int], Optional[pd.DataFrame]]:
    if not qi_cols:
        return None, None

    tmp = df_anon[qi_cols].copy()
    for c in qi_cols:
        tmp[c] = _safe_str_series(tmp[c])

    all_blank = tmp.apply(lambda r: (r == "").all(), axis=1)
    tmp2 = tmp.loc[~all_blank].copy()
    if tmp2.empty:
        return None, None

    group_sizes = tmp2.groupby(qi_cols, dropna=False).size().reset_index(name="class_size")
    k = int(group_sizes["class_size"].min())
    return k, group_sizes

def compute_k_ratios(group_sizes: Optional[pd.DataFrame]) -> Tuple[float, float]:
    if group_sizes is None or group_sizes.empty:
        return 0.0, 0.0
    total = float(group_sizes["class_size"].sum())
    if total <= 0:
        return 0.0, 0.0
    klt2 = float(group_sizes.loc[group_sizes["class_size"] < 2, "class_size"].sum()) / total
    klt5 = float(group_sizes.loc[group_sizes["class_size"] < 5, "class_size"].sum()) / total
    return klt2, klt5

def judge_thresholds(mode: str, policy_consistency: float, pattern_residual: float, high_risk: float) -> bool:
    mode = mode.lower().strip()
    if mode == "high":
        return (policy_consistency >= 0.80) and (pattern_residual <= 0.10) and (high_risk >= 1.0)
    return (policy_consistency >= 0.60) and (pattern_residual <= 0.10) and (high_risk >= 1.0)

def review_flags(mode: str, warn_ratio: float, fail_ratio: float) -> Tuple[bool, bool]:
    mode = mode.lower().strip()
    mandatory = fail_ratio > 0.0
    if mode == "high":
        recommend = warn_ratio >= 0.30
    else:
        recommend = warn_ratio >= 0.50
    return recommend, mandatory

class ValidateGUI:
    def __init__(self, master):
        self.master = master
        master.title("정형 데이터 익명화 검증기 (멀티 파일, report 누적)")
        master.resizable(False, False)

        self.input_paths_var = tk.StringVar()
        self.anon_dir_var = tk.StringVar()     # 익명화 파일 폴더 (비우면 원본 폴더)
        self.report_dir_var = tk.StringVar()   # report 저장 폴더(비우면 원본 폴더)

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

        frame_anon = tk.Frame(master)
        frame_anon.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_anon, text="익명화 파일 폴더 (비우면 원본 폴더에서 자동 탐색)").pack(anchor="w")
        row_anon = tk.Frame(frame_anon)
        row_anon.pack(fill="x")

        self.anon_entry = tk.Entry(row_anon, textvariable=self.anon_dir_var, width=50)
        self.anon_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row_anon, text="폴더 선택...", command=self.browse_anon_dir).pack(side="left", padx=5)

        frame_rep = tk.Frame(master)
        frame_rep.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_rep, text="report 저장 폴더 (비우면 원본 폴더에 저장)").pack(anchor="w")
        row_rep = tk.Frame(frame_rep)
        row_rep.pack(fill="x")

        self.rep_entry = tk.Entry(row_rep, textvariable=self.report_dir_var, width=50)
        self.rep_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row_rep, text="폴더 선택...", command=self.browse_report_dir).pack(side="left", padx=5)

        frame_run = tk.Frame(master)
        frame_run.pack(fill="x", padx=10, pady=10)

        self.run_button = tk.Button(
            frame_run,
            text="검증 실행 (선택된 파일 모두)",
            command=self.run_clicked,
            bg="#2196F3", fg="white"
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

        self.field_label = tk.Label(info_frame, text="처리 중 필드: (검증)", fg="#444", anchor="w")
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

    def set_busy(self, busy: bool):
        if busy:
            self.run_button.config(state="disabled", text="처리 중...", bg="#888888")
        else:
            self.run_button.config(state="normal", text="검증 실행 (선택된 파일 모두)", bg="#2196F3")

    def _reset_job_state(self):
        self._job_error_msg = None
        self._job_error_trace = None
        self.status_label.config(text="")
        self._set_banner("처리 준비 중...")
        self._set_progress(0)
        self.file_label.config(text="처리 중 파일: -")
        self.field_label.config(text="처리 중 필드: (검증)")
        self.eta_label.config(text="예상 남은 시간: -")

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

    def browse_anon_dir(self):
        d = filedialog.askdirectory(title="익명화 파일 폴더 선택")
        if d:
            self.anon_dir_var.set(d)

    def browse_report_dir(self):
        d = filedialog.askdirectory(title="report 저장 폴더 선택")
        if d:
            self.report_dir_var.set(d)

    def _resolve_anonymized_paths(self, orig_path: str, anon_dir: str) -> Tuple[str, str]:
        """
        원본: xxx.csv
        익명화: xxx_anonymized.csv
        로그: xxx_anonymized_log.json
        """
        base = os.path.basename(orig_path)
        stem, ext = os.path.splitext(base)
        anon_name = f"{stem}_anonymized{ext}"
        anon_stem, _ = os.path.splitext(anon_name)
        log_name = anon_stem + "_log.json"

        if anon_dir.strip() == "":
            anon_dir_use = os.path.dirname(orig_path)
        else:
            anon_dir_use = anon_dir.strip()

        anon_path = os.path.join(anon_dir_use, anon_name)
        log_path = os.path.join(anon_dir_use, log_name)
        return anon_path, log_path

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
            anon_dir = self.anon_dir_var.get().strip()
            report_dir = self.report_dir_var.get().strip()
            n_files = len(self._selected_inputs)

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            first_base_dir = os.path.dirname(self._selected_inputs[0])
            report_base_dir = report_dir if report_dir else first_base_dir
            os.makedirs(report_base_dir, exist_ok=True)
            report_path = os.path.join(report_base_dir, f"anonymization_report_{ts}.csv")

            wrote_header = False
            t_global = time.time()

            for idx, orig_path in enumerate(self._selected_inputs, start=1):
                self.master.after(0, lambda: self._set_banner("검증 중..."))
                self.master.after(0, lambda p=orig_path, i=idx, nf=n_files: self.file_label.config(
                    text=f"처리 중 파일: {os.path.basename(p)} ({i}/{nf})"
                ))
                self.master.after(0, lambda: self.field_label.config(text="처리 중 필드: (검증)"))

                anon_path, log_path = self._resolve_anonymized_paths(orig_path, anon_dir)

                if not os.path.exists(anon_path):
                    self.append_log(f"[SKIP] 익명화 파일을 찾을 수 없음: {anon_path}")
                    continue
                if not os.path.exists(log_path):
                    self.append_log(f"[SKIP] log.json을 찾을 수 없음: {log_path}")
                    continue

                df_orig = load_structured(orig_path)
                df_anon = load_structured(anon_path)

                with open(log_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)

                meta = payload.get("_meta", {})
                mode = str(meta.get("mode", "low")).lower().strip()
                allow_dx = bool(meta.get("allow_dx", False))
                log_info = payload.get("log_info", {}) or {}

                start = time.time()
                validator = validate_high if mode == "high" else validate_low
                vres = validator(df_orig=df_orig, df_anon=df_anon, log_info=log_info, diagnosis_allowed=allow_dx)
                duration = time.time() - start

                metrics_df = compute_validation_metrics(
                    df_orig=df_orig,
                    df_anon=df_anon,
                    log_info=log_info,
                    diagnosis_allowed=allow_dx,
                    validation_result=vres,
                    duration_sec=duration
                )
                mrow = metrics_df.iloc[0].to_dict()

                policy_c = float(mrow.get("정책 일관성 준수율", 0.0))
                pattern_r = float(mrow.get("패턴 잔존율", 1.0))

                high_r = mrow.get("고위험 필드 처리율", None)
                if high_r is None:
                    high_r = mrow.get("고위험 컬럼 처리율", 0.0)
                high_r = float(high_r)

                pass_ratio = mrow.get("PASS 비율", None)
                warn_ratio = mrow.get("WARN 비율", None)
                fail_ratio = mrow.get("FAIL 비율", None)

                if pass_ratio is None or warn_ratio is None or fail_ratio is None:
                    total_fields = max(1, len(log_info))  # 정책 적용 대상 컬럼 기준
                    pass_n = len(vres.get("pass", []))
                    warn_n = len(vres.get("warn", []))
                    fail_n = len(vres.get("fail", []))
                    pass_ratio = pass_n / total_fields
                    warn_ratio = warn_n / total_fields
                    fail_ratio = fail_n / total_fields
                else:
                    pass_ratio = float(pass_ratio)
                    warn_ratio = float(warn_ratio)
                    fail_ratio = float(fail_ratio)

                qi_cols = _pick_qi_columns(df_anon, log_info)
                k, gsz = compute_k_group_sizes(df_anon, qi_cols)
                klt2, klt5 = compute_k_ratios(gsz)

                passed = judge_thresholds(mode, policy_c, pattern_r, high_r)
                rec, mand = review_flags(mode, warn_ratio, fail_ratio)

                if passed and (not rec) and (not mand):
                    result_str = "PASS"
                elif (not passed) or mand:
                    result_str = "FAIL"
                else:
                    result_str = "WARN"

                report_row = {
                    "파일명": os.path.basename(orig_path),
                    "익명화 결과": result_str,
                    "정책 일관성 준수율(%)": round(policy_c * 100, 2),
                    "패턴 잔존율(%)": round(pattern_r * 100, 2),
                    "고위험 필드 처리율(%)": round(high_r * 100, 2),
                    "PASS 비율(%)": round(pass_ratio * 100, 2),
                    "WARN 비율(%)": round(warn_ratio * 100, 2),
                    "FAIL 비율(%)": round(fail_ratio * 100, 2),
                    "추가 검토 여부": bool(rec),
                    "필수 검토 여부": bool(mand),
                    "k < 2 비율(%)": round(klt2 * 100, 2),
                    "k < 5 비율(%)": round(klt5 * 100, 2),
                    "처리 시간(초)": round(float(duration), 2),
                }

                # 누적 저장
                df_rep = pd.DataFrame([report_row])
                if (not os.path.exists(report_path)) or (not wrote_header):
                    save_csv(df_rep, report_path, append=False)
                    wrote_header = True
                else:
                    save_csv(df_rep, report_path, append=True)

                self.append_log(f"[{result_str}] {os.path.basename(orig_path)} -> report 누적됨")
                self.append_log(f"report: {report_path}")

                # 안전 판정 시 원본 삭제 (문서 요구)
                if passed and (not rec) and (not mand):
                    try:
                        os.remove(orig_path)
                        self.append_log(f"[PASS] 안전 기준 통과 -> 원본 삭제됨: {os.path.basename(orig_path)}")
                    except Exception as e:
                        self.append_log(f"[WARN] 원본 삭제 실패: {os.path.basename(orig_path)} ({e})")

                pct = (idx / max(1, n_files)) * 100.0
                self.master.after(0, lambda pc=pct: self._set_progress(pc))

            self.master.after(0, lambda: self.append_log("=== 검증 작업 완료 ==="))
            self.master.after(0, lambda: self.append_log(f"최종 report: {report_path}"))

        except Exception as e:
            self._job_error_msg = str(e)
            self._job_error_trace = traceback.format_exc()
        finally:
            self.master.after(0, self._finish_ui)

    def _finish_ui(self):
        self.set_busy(False)

        if self._job_error_msg:
            self._set_banner("검증 실패")
            self.status_label.config(text="검증 실패 (하단 로그 확인)")
            messagebox.showerror("검증 실패", f"{self._job_error_msg}\n\n하단 로그를 확인하세요.")
            self.append_log("[ERROR] " + self._job_error_msg)
            if self._job_error_trace:
                for line in self._job_error_trace.splitlines():
                    self.append_log(line)
            return

        self._set_banner("검증 완료")
        self._set_progress(100)
        self.status_label.config(text="검증 완료: report CSV에 누적 저장됨")
        messagebox.showinfo("검증 완료", "검증이 완료되었습니다.\nreport CSV에 파일별 행이 누적 저장되었습니다.")
        self.append_log("=== UI 종료 대기 ===")


def launch():
    logging.basicConfig(level=logging.ERROR)
    root = tk.Tk()
    app = ValidateGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
