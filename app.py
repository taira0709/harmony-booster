# -*- coding: utf-8 -*-
# app.py（4タブ + 短いプリセット表示/ASCIIハイフンに統一）

import os
import tempfile
import streamlit as st

# ---------- Page config ----------
st.set_page_config(page_title="Harmony Booster", page_icon="🎵", layout="centered")

# ---------- Login ----------
def check_password() -> bool:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if st.session_state.auth_ok:
        return True

    st.title("ハーモニーブースター ログインページ")
    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("パスワードを入力してください", type="password")
        ok = st.form_submit_button("ログイン")
    if ok:
        expected = os.environ.get("APP_PASSWORD", "hb2025")
        if pwd == expected:
            st.session_state.auth_ok = True
            st.success("ログインしました。"); st.rerun()
        else:
            st.error("パスワードが違います。")
    return False

if not check_password():
    st.stop()

# ---------- Utils ----------
def guess_mime_from_name(file_name: str) -> str:
    ext = (os.path.splitext(file_name)[1] or "").lower()
    mapping = {
        ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
        ".mp4": "audio/mp4", ".flac": "audio/flac", ".ogg": "audio/ogg",
        ".oga": "audio/ogg", ".aif": "audio/aiff", ".aiff": "audio/aiff",
    }
    return mapping.get(ext, "audio/wav")

def init_state():
    s = st.session_state
    s.setdefault("upload_name", None)
    s.setdefault("upload_bytes", None)
    s.setdefault("upload_mime", None)
    # プリセット関連（短い英数表示に統一）
    s.setdefault("preset", "Pop 2-6k")
    s.setdefault("band_low", 200.0)
    s.setdefault("band_high", 6000.0)
    s.setdefault("mid_atten_db", -8.0)
    s.setdefault("side_gain_db", 0.0)
    s.setdefault("protect_low_hz", 120.0)
    s.setdefault("protect_high_hz", 8000.0)
    s.setdefault("output_gain_db", 0.0)

# プリセット定義（表示ラベルを短く）
PRESET_OPTIONS = [
    "Pop 2-6k",
    "Rock 3-8k",
    "Male 120-4k",
    "Female 200-10k",
    "Aggressive 1-7k",
    "Custom",
]
PRESET_PARAMS = {
    "Pop 2-6k":        dict(band_low=200.0,  band_high=6000.0,  mid_atten_db=-8.0,  side_gain_db=0.0),
    "Rock 3-8k":       dict(band_low=300.0,  band_high=8000.0,  mid_atten_db=-10.0, side_gain_db=1.5),
    "Male 120-4k":     dict(band_low=120.0,  band_high=4000.0,  mid_atten_db=-6.0,  side_gain_db=0.0),
    "Female 200-10k":  dict(band_low=200.0,  band_high=10000.0, mid_atten_db=-7.0,  side_gain_db=1.0),
    "Aggressive 1-7k": dict(band_low=1000.0, band_high=7000.0,  mid_atten_db=-12.0, side_gain_db=2.0),
}

def apply_preset(name: str):
    if name in PRESET_PARAMS:
        for k, v in PRESET_PARAMS[name].items():
            st.session_state[k] = v

def clamp_band():
    s = st.session_state
    if s["band_low"] >= s["band_high"]:
        s["band_high"] = max(s["band_low"] + 100.0, s["band_high"])

init_state()

# ---------- UI ----------
st.title("🎵 ハーモニーブースター")
with st.expander("使い方（タップで開く）", expanded=False):
    st.markdown(
        "1) ①ファイルで音声を選ぶ\n"
        "2) ②プリセットで帯域/Mid-Side などを調整\n"
        "3) ③プレビューで確認\n"
        "4) ④書き出しで高品質処理 → ダウンロード"
    )

tabs = st.tabs(["①ファイル", "②プリセット", "③プレビュー", "④書き出し"])

# ---- ① ファイル ----
with tabs[0]:
    uploaded = st.file_uploader(
        "音源をアップロード",
        type=["wav","mp3","m4a","flac","ogg","aiff","aif"],
        accept_multiple_files=False,
        help="1ファイルあたり200MBまで（必要に応じて変更可）",
    )
    if uploaded:
        st.session_state.upload_name = uploaded.name
        st.session_state.upload_bytes = uploaded.getbuffer().tobytes()
        st.session_state.upload_mime  = guess_mime_from_name(uploaded.name)
        st.success(f"読み込み完了: {uploaded.name}")

# ---- ② プリセット ----
with tabs[1]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        preset = st.selectbox(
            "ボーカル帯域プリセット（k=1000Hz）",
            PRESET_OPTIONS,
            index=PRESET_OPTIONS.index(st.session_state.preset) if st.session_state.preset in PRESET_OPTIONS else 0,
            help="記法例: 2-6k = 2〜6kHz",
        )
        if preset != st.session_state.preset:
            st.session_state.preset = preset
            if preset != "Custom":
                apply_preset(preset)

        c1, c2 = st.columns(2)
        with c1:
            st.number_input(
                "帯域 Low (Hz)", 50.0, 12000.0, key="band_low", step=10.0, format="%.1f",
                disabled=(st.session_state.preset != "Custom"),
            )
        with c2:
            st.number_input(
                "帯域 High (Hz)", 200.0, 20000.0, key="band_high", step=10.0, format="%.1f",
                disabled=(st.session_state.preset != "Custom"),
            )
        clamp_band()
        st.caption(f"現在の帯域: {st.session_state.band_low:.0f} Hz - {st.session_state.band_high:.0f} Hz")

        st.subheader("Mid / Side バランス")
        c3, c4 = st.columns(2)
        with c3:
            st.slider("Mid Atten (dB)", -24.0, 6.0, key="mid_atten_db")
        with c4:
            st.slider("Side Gain (dB)", -12.0, 12.0, key="side_gain_db")

        st.subheader("Protect（低域/高域の保護）")
        p1, p2 = st.columns(2)
        with p1:
            st.number_input("Protect Low (Hz)", 20.0, 400.0, key="protect_low_hz", step=10.0, format="%.1f")
        with p2:
            st.number_input("Protect High (Hz)", 4000.0, 20000.0, key="protect_high_hz", step=100.0, format="%.1f")

        st.subheader("出力ゲイン")
        st.slider("Output Gain (dB)", -12.0, 12.0, key="output_gain_db")

        st.info(
            f"設定: Band {st.session_state.band_low:.0f}-{st.session_state.band_high:.0f} Hz / "
            f"Mid {st.session_state.mid_atten_db:.1f} dB / Side {st.session_state.side_gain_db:.1f} dB / "
            f"Protect {st.session_state.protect_low_hz:.0f}-{st.session_state.protect_high_hz:.0f} Hz / "
            f"Out {st.session_state.output_gain_db:.1f} dB"
        )

# ---- ③ プレビュー ----
with tabs[2]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        mime = st.session_state.upload_mime or guess_mime_from_name(st.session_state.upload_name or "")
        st.audio(st.session_state.upload_bytes, format=mime)
        st.caption(
            f"{st.session_state.upload_name} / {mime} | "
            f"Band {st.session_state.band_low:.0f}-{st.session_state.band_high:.0f} Hz, "
            f"Mid {st.session_state.mid_atten_db:.1f} dB, Side {st.session_state.side_gain_db:.1f} dB"
        )
        st.write("※ プレビューは原音の再生。書き出し時に設定を適用します。")

# ---- ④ 書き出し ----
with tabs[3]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        if st.button("高品質で処理してダウンロード", type="primary"):
            in_suffix = os.path.splitext(st.session_state.upload_name or "")[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as tmp_in:
                tmp_in.write(st.session_state.upload_bytes); tmp_in.flush()
                in_path = tmp_in.name

            try:
                from ms_vocal_attenuator import run_file as _run_file
            except Exception as e:
                st.error(f"処理モジュールの読み込みに失敗しました: {e}")
                try: os.unlink(in_path)
                except Exception: pass
            else:
                try:
                    result = _run_file(
                        in_path,
                        vocal_band=(float(st.session_state.band_low), float(st.session_state.band_high)),
                        mid_atten_db=float(st.session_state.mid_atten_db),
                        side_gain_db=float(st.session_state.side_gain_db),
                        protect_low_hz=float(st.session_state.protect_low_hz),
                        protect_high_hz=float(st.session_state.protect_high_hz),
                        output_gain_db=float(st.session_state.output_gain_db),
                    )
                    out_path = result[0] if isinstance(result, tuple) else result
                    file_name = os.path.basename(out_path) or f"output{in_suffix}"
                    mime = "audio/wav" if out_path.lower().endswith(".wav") else "application/octet-stream"
                    with open(out_path, "rb") as f:
                        st.download_button("結果をダウンロード", data=f, file_name=file_name, mime=mime)
                    st.success("書き出しが完了しました。")
                except Exception as e:
                    st.error(f"処理中にエラーが発生しました: {e}")
                finally:
                    try: os.unlink(in_path)
                    except Exception: pass
