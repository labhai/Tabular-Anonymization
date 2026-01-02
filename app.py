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
from typing import List, Dict, Any, Optional, Tuple

from anonymize.semantics import guess_semantic_field
from anonymize.transforms import transform_series

from policy.policy_low import policy_low
from policy.policy_high import policy_high

from validation.validation_low import validate_low
from validation.validation_high import validate_high

from validation.validation_common import compute_validation_metrics

def _safe_str_series(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()


def _pick_qi_columns(df_anon: pd.DataFrame, log_info: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    QI(준식별자) 후보 컬럼 선정
    - log_info의 semantic을 우선 활용
    - drop된 컬럼은 애초에 df_anon에 없으므로 자동 제외
    """
    # 보고서 서술(준식별자) 범위에 맞춰 과도한 QI 선택을 피하도록 구성
    qi_semantic_allow = {
        "age", "gender", "race", "ethnicity",
        "marital_status", "address", "zipcode",
        "visit_date", "birthdate", "deathdate",
        "location"
    }

    qi_cols: List[str] = []
    for c in df_anon.columns:
        sem = str(log_info.get(c, {}).get("semantic", "")).lower().strip()
        action = str(log_info.get(c, {}).get("action", "")).lower().strip()
        if action == "drop":
            continue
        if sem in qi_semantic_allow:
            qi_cols.append(c)
    return qi_cols


def _pick_sensitive_columns(df_anon: pd.DataFrame, log_info: Dict[str, Dict[str, Any]]) -> List[str]:
    sa_semantic_allow = {
        "diagnosis", "measurement", "comment", "note", "finance"
    }

    sa_cols: List[str] = []
    for c in df_anon.columns:
        sem = str(log_info.get(c, {}).get("semantic", "")).lower().strip()
        action = str(log_info.get(c, {}).get("action", "")).lower().strip()
        if action == "drop":
            continue
        if sem in sa_semantic_allow:
            sa_cols.append(c)
    return sa_cols


def compute_k_anonymity(df_anon: pd.DataFrame, qi_cols: List[str]) -> Tuple[Optional[int], Optional[pd.DataFrame]]:
    if not qi_cols:
        return None, None

    tmp = df_anon[qi_cols].copy()
    for c in qi_cols:
        tmp[c] = _safe_str_series(tmp[c])

    all_blank = (tmp.apply(lambda r: (r == "").all(), axis=1))
    tmp2 = tmp.loc[~all_blank].copy()
    if tmp2.empty:
        return None, None

    group_sizes = tmp2.groupby(qi_cols, dropna=False).size().reset_index(name="class_size")
    k = int(group_sizes["class_size"].min())
    return k, group_sizes


def compute_k_ratios(group_sizes: Optional[pd.DataFrame]) -> Tuple[float, float]:
    """
    k<2 비율, k<5 비율을 레코드 비율로 계산.
    (equivalence class size를 레코드 수로 가중)
    """
    if group_sizes is None or group_sizes.empty:
        return 0.0, 0.0
    total = float(group_sizes["class_size"].sum())
    if total <= 0:
        return 0.0, 0.0
    klt2 = float(group_sizes.loc[group_sizes["class_size"] < 2, "class_size"].sum()) / total
    klt5 = float(group_sizes.loc[group_sizes["class_size"] < 5, "class_size"].sum()) / total
    return klt2, klt5


def compute_l_diversity(df_anon: pd.DataFrame, qi_cols: List[str], sensitive_col: str) -> Optional[int]:
    """
    distinct l-diversity: 각 equivalence class 내에서 SA의 distinct count 최소값.
    """
    if (not qi_cols) or (sensitive_col not in df_anon.columns):
        return None

    tmp = df_anon[qi_cols + [sensitive_col]].copy()
    for c in qi_cols:
        tmp[c] = _safe_str_series(tmp[c])
    tmp[sensitive_col] = _safe_str_series(tmp[sensitive_col])

    tmp = tmp[tmp[sensitive_col] != ""]
    if tmp.empty:
        return None

    l_series = tmp.groupby(qi_cols, dropna=False)[sensitive_col].nunique()
    if l_series.empty:
        return None
    return int(l_series.min())


def _total_variation_distance(p: pd.Series, q: pd.Series) -> float:
    """
    Categorical 분포 간 Total Variation Distance: 0.5 * sum |p - q|
    """
    all_idx = p.index.union(q.index)
    p2 = p.reindex(all_idx).fillna(0.0)
    q2 = q.reindex(all_idx).fillna(0.0)
    return float(0.5 * np.abs(p2.values - q2.values).sum())


def compute_t_closeness(df_anon: pd.DataFrame, qi_cols: List[str], sensitive_col: str) -> Optional[float]:
    """
    t-closeness (categorical): 각 class의 SA 분포와 전체 SA 분포 간 TV distance의 최대값.
    """
    if (not qi_cols) or (sensitive_col not in df_anon.columns):
        return None

    tmp = df_anon[qi_cols + [sensitive_col]].copy()
    for c in qi_cols:
        tmp[c] = _safe_str_series(tmp[c])
    tmp[sensitive_col] = _safe_str_series(tmp[sensitive_col])

    tmp = tmp[tmp[sensitive_col] != ""]
    if tmp.empty:
        return None

    overall = tmp[sensitive_col].value_counts(normalize=True)

    max_dist = 0.0
    for _, g in tmp.groupby(qi_cols, dropna=False):
        pg = g[sensitive_col].value_counts(normalize=True)
        d = _total_variation_distance(pg, overall)
        if d > max_dist:
            max_dist = d

    return float(max_dist)


def compute_privacy_metrics(
    df_anon: pd.DataFrame,
    log_info: Dict[str, Dict[str, Any]],
    qi_cols: Optional[List[str]] = None,
    sensitive_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    반환:
    - privacy_df: SA별 l/t 포함, k 포함
    - summary: 로그 출력용 요약 dict (+ k<2/k<5 비율)
    """
    if qi_cols is None:
        qi_cols = _pick_qi_columns(df_anon, log_info)
    if sensitive_cols is None:
        sensitive_cols = _pick_sensitive_columns(df_anon, log_info)

    k, group_sizes = compute_k_anonymity(df_anon, qi_cols)
    klt2, klt5 = compute_k_ratios(group_sizes)

    rows = []
    if not sensitive_cols:
        rows.append({
            "QI 컬럼": ",".join(qi_cols),
            "SA 컬럼": "",
            "k-익명성(k)": k if k is not None else "",
            "l-다양성(l)": "",
            "t-근접성(t)": "",
            "비고": "SA(민감속성) 후보가 없어 l/t 계산 생략"
        })
    else:
        for sa in sensitive_cols:
            l = compute_l_diversity(df_anon, qi_cols, sa)
            t = compute_t_closeness(df_anon, qi_cols, sa)
            rows.append({
                "QI 컬럼": ",".join(qi_cols),
                "SA 컬럼": sa,
                "k-익명성(k)": k if k is not None else "",
                "l-다양성(l)": l if l is not None else "",
                "t-근접성(t)": (round(t, 6) if t is not None else ""),
                "비고": ""
            })

    privacy_df = pd.DataFrame(rows)

    l_values = [r["l-다양성(l)"] for r in rows if r.get("l-다양성(l)") not in ("", None)]
    t_values = [r["t-근접성(t)"] for r in rows if r.get("t-근접성(t)") not in ("", None)]

    summary = {
        "qi_cols": qi_cols,
        "sensitive_cols": sensitive_cols,
        "k": k,
        "klt2": klt2,
        "klt5": klt5,
        "l_min": (min(l_values) if l_values else None),
        "t_max": (max(t_values) if t_values else None),
    }
    return privacy_df, summary

def _metric_get(mrow: pd.Series, keys: List[str], default: float) -> float:
    for k in keys:
        if k in mrow and mrow.get(k) is not None:
            try:
                return float(mrow.get(k))
            except Exception:
                pass
    return float(default)


def _compute_pass_warn_fail_ratio(report: Dict[str, List[str]], total_cols: int) -> Tuple[float, float, float]:
    """
    PASS/WARN/FAIL 비율을 '필드 단위 판정' 기반으로 계산
    """
    p = len(report.get("pass", []))
    w = len(report.get("warn", []))
    f = len(report.get("fail", []))
    total = max(1, total_cols if total_cols > 0 else (p + w + f))
    return p / total, w / total, f / total


def _judge_thresholds(mode: str, policy_consistency: float, pattern_residual: float, high_risk: float) -> bool:
    mode = (mode or "").lower().strip()
    if mode == "high":
        return (policy_consistency >= 0.80) and (pattern_residual <= 0.10) and (high_risk >= 1.0)
    return (policy_consistency >= 0.60) and (pattern_residual <= 0.10) and (high_risk >= 1.0)


def _review_flags(mode: str, warn_ratio: float, fail_ratio: float) -> Tuple[bool, bool]:
    """
    - FAIL 비율 > 0 => 필수 검토
    - 저수준 WARN 비율 >= 50% => 추가 검토 권장
    - 고수준 WARN 비율 >= 30% => 추가 검토 권장
    """
    mode = (mode or "").lower().strip()
    mandatory = fail_ratio > 0.0
    if mode == "high":
        recommend = warn_ratio >= 0.30
    else:
        recommend = warn_ratio >= 0.50
    return recommend, mandatory

class AnonymizerGUI:
    def __init__(self, master):
        self.master = master
        master.title("의료데이터 익명화 도구")

        self.input_paths_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="low")
        self.allow_dx_var = tk.BooleanVar(value=False)

        self._selected_inputs: List[str] = []

        self._job_error_msg: Optional[str] = None
        self._job_error_trace: Optional[str] = None

        self._results: Dict[str, Dict[str, Any]] = {}

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

        self.run_anon_button = tk.Button(
            frame_run,
            text="1) 익명화 실행 (선택된 파일 모두)",
            command=self.run_anonymization_clicked,
            bg="#4CAF50", fg="white"
        )
        self.run_anon_button.pack(fill="x")

        self.run_validate_button = tk.Button(
            frame_run,
            text="2) 검증 실행 (익명화 완료된 파일)",
            command=self.run_validation_clicked,
            bg="#2196F3", fg="white",
            state="disabled"
        )
        self.run_validate_button.pack(fill="x", pady=(6, 0))

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

    def _force_series_1d(self, obj, col_name_for_log: str) -> pd.Series:
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

    def _promote_first_row_header(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        cols = list(df.columns)
        unnamed_ratio = sum([str(c).startswith("Unnamed") for c in cols]) / len(cols)
        if unnamed_ratio >= 0.5:
            new_header = df.iloc[0].astype(str).tolist()
            df2 = df.iloc[1:].copy()
            df2.columns = new_header
            df2.reset_index(drop=True, inplace=True)
            return df2
        return df

    def _guess_ext(self, path: str) -> str:
        return os.path.splitext(path)[1].lower()

    def _load_input_dataframe(self, path: str) -> pd.DataFrame:
        ext = self._guess_ext(path)
        if ext == ".csv":
            df_raw = pd.read_csv(path)
        elif ext in [".xlsx", ".xls"]:
            df_raw = pd.read_excel(path)
        else:
            raise ValueError(f"지원하지 않는 입력 형식입니다: {ext} (csv/xlsx/xls만 가능)")
        return self._promote_first_row_header(df_raw)

    def _save_output_dataframe(self, df: pd.DataFrame, path: str):
        ext = self._guess_ext(path)
        if ext == ".csv":
            df.to_csv(path, index=False, encoding="utf-8-sig")
        elif ext in [".xlsx", ".xls"]:
            df.to_excel(path, index=False)
        else:
            fallback = path + ".csv"
            df.to_csv(fallback, index=False, encoding="utf-8-sig")
            raise ValueError(f"알 수 없는 출력 확장자라서 CSV로 저장했습니다: {fallback}")

    def _build_output_path(self, input_path: str, output_dir: str) -> str:
        base_name = os.path.basename(input_path)
        stem, ext = os.path.splitext(base_name)
        out_name = f"{stem}_anonymized{ext}"
        if output_dir.strip() == "":
            return os.path.join(os.path.dirname(input_path), out_name)
        return os.path.join(output_dir, out_name)

    def _build_metrics_path(self, out_path: str) -> str:
        lowp = out_path.lower()
        if lowp.endswith(".csv"):
            return out_path[:-4] + "_metrics.csv"
        if lowp.endswith(".xlsx"):
            return out_path[:-5] + "_metrics.csv"
        if lowp.endswith(".xls"):
            return out_path[:-4] + "_metrics.csv"
        return out_path + "_metrics.csv"

    def _build_privacy_path(self, out_path: str) -> str:
        lowp = out_path.lower()
        if lowp.endswith(".csv"):
            return out_path[:-4] + "_privacy.csv"
        if lowp.endswith(".xlsx"):
            return out_path[:-5] + "_privacy.csv"
        if lowp.endswith(".xls"):
            return out_path[:-4] + "_privacy.csv"
        return out_path + "_privacy.csv"

    def _build_global_report_path(self, output_dir: str, first_input_path: str, mode: str) -> str:
        """
        배치 전체 누적 report CSV (첨부 양식처럼 1행=1파일)
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"anonymization_report_{mode}_{ts}.csv"
        base_dir = output_dir if output_dir.strip() else os.path.dirname(first_input_path)
        return os.path.join(base_dir, name)

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
            self.run_anon_button.config(state="disabled", text="처리 중...", bg="#888888")
            self.run_validate_button.config(state="disabled", bg="#888888")
        else:
            self.run_anon_button.config(state="normal", text="1) 익명화 실행 (선택된 파일 모두)", bg="#4CAF50")
            if len(self._results) > 0:
                self.run_validate_button.config(state="normal", bg="#2196F3")
            else:
                self.run_validate_button.config(state="disabled", bg="#2196F3")

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

        self._results.clear()
        self.run_validate_button.config(state="disabled")
        self.append_log(f"입력 파일 {len(self._selected_inputs)}개 선택됨. 이전 결과 캐시 초기화.")

    def browse_output_dir(self):
        d = filedialog.askdirectory(title="출력 폴더 선택")
        if d:
            self.output_dir_var.set(d)

    def run_anonymization_clicked(self):
        if not self._selected_inputs:
            messagebox.showerror("오류", "원본 파일을 1개 이상 선택하세요.")
            return

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self._reset_job_state()
        self.set_busy(True)

        worker = threading.Thread(target=self.run_anonymization_job_multi, daemon=True)
        worker.start()

    def run_anonymization_job_multi(self):
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
                    df_tmp = self._load_input_dataframe(p)
                    per_file_cols[p] = len(df_tmp.columns)
                    total_cols_all += len(df_tmp.columns)
                except Exception as e:
                    per_file_cols[p] = 0
                    self.master.after(0, lambda m=f"[SKIP] 파일 로드 실패: {p} ({e})": self.append_log(m))

            if total_cols_all == 0:
                raise RuntimeError("처리 가능한 컬럼이 없습니다. (모든 파일 로드 실패 또는 빈 파일)")

            completed_cols = 0
            t_global = time.time()

            self._results.clear()

            for file_idx, input_path in enumerate(self._selected_inputs, start=1):
                n_cols = per_file_cols.get(input_path, 0)
                if n_cols <= 0:
                    continue

                t_file0 = time.time()

                df_orig = self._load_input_dataframe(input_path)
                cols = list(df_orig.columns)

                self.master.after(0, lambda i=file_idx, nf=n_files, p=input_path: self.append_log(
                    f"=== [{i}/{nf}] 익명화 시작: {p} (cols={len(cols)}) ==="
                ))

                out_cols = {}
                log_info = {}

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
                            out_cols[safe_key] = self._force_series_1d(sub_df[subcol], safe_key)
                            log_info[safe_key] = {"semantic": sem, "action": action, "source": c}
                    else:
                        out_cols[c] = self._force_series_1d(new_series, c)
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
                out_path = self._build_output_path(input_path, output_dir)
                self._save_output_dataframe(anon_df, out_path)

                duration_sec = time.time() - t_file0

                self._results[input_path] = {
                    "df_orig": df_orig,
                    "df_anon": anon_df,
                    "log_info": log_info,
                    "output_path": out_path,
                    "mode": mode,
                    "allow_dx": allow_dx,
                    "duration_sec": duration_sec,
                }

                self.master.after(0, lambda op=out_path: self.append_log(f"익명화 저장 완료: {op}"))

            if len(self._results) == 0:
                raise RuntimeError("익명화가 완료된 파일이 없습니다. (모든 파일이 스킵되었을 수 있음)")

        except Exception as e:
            self._job_error_msg = str(e)
            self._job_error_trace = traceback.format_exc()
        finally:
            self.master.after(0, self.finish_anonymization_ui)

    def finish_anonymization_ui(self):
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
        self.status_label.config(text=f"익명화 완료: {len(self._results)}개 파일 저장됨")
        self.run_validate_button.config(state="normal")
        messagebox.showinfo("익명화 완료", f"익명화 완료: {len(self._results)}개 파일\n이제 검증(2번)을 실행할 수 있습니다.")
        self.append_log("=== 익명화 작업 완료 ===")

    def run_validation_clicked(self):
        if len(self._results) == 0:
            messagebox.showwarning("안내", "검증을 실행하려면 먼저 익명화를 완료해야 합니다.")
            return

        self._job_error_msg = None
        self._job_error_trace = None
        self.set_busy(True)
        self._set_banner("검증 시작...")
        self._set_progress(0)

        worker = threading.Thread(target=self.run_validation_job_multi, daemon=True)
        worker.start()

    def run_validation_job_multi(self):
        try:
            items = list(self._results.items())
            n_files = len(items)

            output_dir = self.output_dir_var.get().strip()
            first_input_path = items[0][0]
            mode_for_name = (items[0][1].get("mode") or "low")
            report_path_global = self._build_global_report_path(output_dir, first_input_path, mode_for_name)

            wrote_header = False

            for idx, (input_path, meta) in enumerate(items, start=1):
                t_val0 = time.time()

                mode = meta["mode"]
                allow_dx = meta["allow_dx"]
                df_orig = meta["df_orig"]
                df_anon = meta["df_anon"]
                log_info = meta["log_info"]
                out_path = meta["output_path"]
                duration_anon = float(meta.get("duration_sec") or 0.0)

                self.master.after(0, lambda: self._set_banner("검증 중..."))
                self.master.after(0, lambda ft=f"처리 중 파일: {os.path.basename(input_path)} ({idx}/{n_files})": self.file_label.config(text=ft))
                self.master.after(0, lambda fld="처리 중 필드: (검증 단계)": self.field_label.config(text=fld))
                self.master.after(0, lambda et="예상 남은 시간: -": self.eta_label.config(text=et))

                validator = validate_high if mode == "high" else validate_low
                report = validator(df_orig=df_orig, df_anon=df_anon, log_info=log_info, diagnosis_allowed=allow_dx)

                metrics_df = compute_validation_metrics(
                    df_orig=df_orig,
                    df_anon=df_anon,
                    log_info=log_info,
                    diagnosis_allowed=allow_dx,
                    validation_result=report,
                    duration_sec=0.0
                )
                metrics_path = self._build_metrics_path(out_path)
                metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")

                privacy_df, privacy_summary = compute_privacy_metrics(df_anon=df_anon, log_info=log_info)
                privacy_path = self._build_privacy_path(out_path)
                privacy_df.to_csv(privacy_path, index=False, encoding="utf-8-sig")

                mrow = metrics_df.iloc[0]

                total_cols = int(mrow.get("총 컬럼 수", len(df_anon.columns)))
                policy_consistency = _metric_get(mrow, ["정책 일관성 준수율", "policy_consistency"], 0.0)
                pattern_residual = _metric_get(mrow, ["패턴 잔존율", "pattern_residual"], 1.0)
                high_risk_rate = _metric_get(mrow, ["고위험 필드 처리율", "고위험 컬럼 처리율", "high_risk_coverage"], 0.0)

                pass_ratio, warn_ratio, fail_ratio = _compute_pass_warn_fail_ratio(report, total_cols)

                passed = _judge_thresholds(mode, policy_consistency, pattern_residual, high_risk_rate)
                rec, mand = _review_flags(mode, warn_ratio, fail_ratio)

                if passed and (not rec) and (not mand):
                    final_label = "PASS"
                elif (not passed) or mand:
                    final_label = "FAIL"
                else:
                    final_label = "WARN"

                k = privacy_summary.get("k")
                klt2 = float(privacy_summary.get("klt2") or 0.0)
                klt5 = float(privacy_summary.get("klt5") or 0.0)

                duration_val = time.time() - t_val0
                duration_total = duration_anon + duration_val

                report_row = {
                    "파일명": os.path.basename(input_path),
                    "익명화 결과": final_label,
                    "정책 일관성 준수율(%)": round(policy_consistency * 100, 2),
                    "패턴 잔존율(%)": round(pattern_residual * 100, 2),
                    "고위험 필드 처리율(%)": round(high_risk_rate * 100, 2),
                    "PASS 비율(%)": round(pass_ratio * 100, 2),
                    "WARN 비율(%)": round(warn_ratio * 100, 2),
                    "FAIL 비율(%)": round(fail_ratio * 100, 2),
                    "추가 검토 여부": bool(rec),
                    "필수 검토 여부": bool(mand),
                    "k < 2 비율(%)": round(klt2 * 100, 2),
                    "k < 5 비율(%)": round(klt5 * 100, 2),
                    "처리 시간(초)": round(float(duration_total), 2),
                }

                df_rep = pd.DataFrame([report_row])
                if (not os.path.exists(report_path_global)) or (not wrote_header):
                    df_rep.to_csv(report_path_global, index=False, encoding="utf-8-sig")
                    wrote_header = True
                else:
                    df_rep.to_csv(report_path_global, mode="a", header=False, index=False, encoding="utf-8-sig")

                self.master.after(0, lambda s=f"[{final_label}] {os.path.basename(input_path)} | "
                                              f"policy={policy_consistency:.3f} pattern={pattern_residual:.3f} highrisk={high_risk_rate:.3f} | "
                                              f"PASS/WARN/FAIL={pass_ratio:.2f}/{warn_ratio:.2f}/{fail_ratio:.2f} | "
                                              f"k={report_row['k(최소 equivalence class)']} k<2={klt2:.3f} k<5={klt5:.3f} | "
                                              f"report={os.path.basename(report_path_global)}": self.append_log(s))
                self.master.after(0, lambda mp=metrics_path: self.append_log(f"metrics 저장: {mp}"))
                self.master.after(0, lambda pp=privacy_path: self.append_log(f"privacy 저장: {pp}"))
                self.master.after(0, lambda rp=report_path_global: self.append_log(f"누적 report 저장: {rp}"))

                pct = (idx / n_files) * 100.0
                self.master.after(0, lambda pc=pct: self._set_progress(pc))

            self.master.after(0, lambda rp=report_path_global: self.append_log(f"=== 배치 누적 report 완료: {rp} ==="))
            self._final_report_path = report_path_global

        except Exception as e:
            self._job_error_msg = str(e)
            self._job_error_trace = traceback.format_exc()
        finally:
            self.master.after(0, self.finish_validation_ui)

    def finish_validation_ui(self):
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

        rp = getattr(self, "_final_report_path", None)
        if rp:
            self.status_label.config(text=f"검증 완료: 누적 report 저장됨 ({os.path.basename(rp)})")
            messagebox.showinfo("검증 완료", f"검증이 완료되었습니다.\n누적 report: {rp}")
        else:
            self.status_label.config(text="검증 완료: 누적 report 저장됨")
            messagebox.showinfo("검증 완료", "검증이 완료되었습니다.\n누적 report가 저장되었습니다.")

        self.append_log("=== 검증 작업 완료 ===")


def launch():
    root = tk.Tk()
    root.resizable(False, False)
    app = AnonymizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
