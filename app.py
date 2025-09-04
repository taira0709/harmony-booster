# -*- coding: utf-8 -*-
# app.py（MIME 自動判定で st.audio を安定化）

import os
import tempfile
import streamlit as st

# =========================
# ページ設定（最初に呼ぶ）
# =========================
st.set_page_config(page_title="Harmony Booster", page_icon="🎵", layout="centered")


# =========================
# ログイン（フォーム＋送信ボタン）
# =========================
def check_password() -> bool:
    """APP_PASSWORD（未設定時は 'hb2025'）で認証。OKなら True。"""
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
            st.success("ログインしました。")
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


# ログイン未完了ならアプリ本体を停止
if not check_password():
    st.stop()


# =========================
# ユーティリティ
# =========================
def guess_mime_from_name(file_name: str) -> str:
    ext = (os.path.splitext(file_name)[1] or "").lower()
    mapping = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",    # audio/mp3 より互換が広い
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".aif": "audio/aiff",
        ".aiff": "audio/aiff",
    }
    return mapping.get(ext, "audio/wav")  # 不明なら wav にフォールバック


# =========================
# ここからアプリ本体
# =========================
st.title("🎵 ハーモニーブースター")

with st.expander("使い方（タップで開く）", expanded=False):
    st.markdown(
        "1) 下で音声ファイルを選ぶ\n"
        "2) プレビューで再生して確認\n"
        "3) 書き出しボタンで高品質処理 → ダウンロード"
    )

tabs = st.tabs(["①ファイル", "②プレビュー", "③書き出し"])

# ---- ① ファイル選択 ----
with tabs[0]:
    uploaded = st.file_uploader(
        "音源をアップロード",
        type=["wav", "mp3", "m4a", "flac", "ogg", "aiff", "aif"],
        accept_multiple_files=False,
        help="1ファイルあたり200MBまで（必要に応じて変更可能）",
    )

    if uploaded:
        st.session_state.upload_name = uploaded.name
        st.session_state.upload_bytes = uploaded.getbuffer().tobytes()
        st.session_state.upload_mime = guess_mime_from_name(uploaded.name)
        st.success(f"読み込み完了: {uploaded.name}")

# ---- ② プレビュー ----
with tabs[1]:
    if "upload_bytes" not in st.session_state:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        mime = st.session_state.get("upload_mime", guess_mime_from_name(st.session_state.get("upload_name", "")))
        # ★ 重要：bytes を渡す時は format= に MIME を指定
        st.audio(st.session_state.upload_bytes, format=mime)
        st.caption(f"{st.session_state.get('upload_name','')}  /  {mime}")

# ---- ③ 書き出し ----
with tabs[2]:
    if "upload_bytes" not in st.session_state:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            run_btn = st.button("高品質で処理してダウンロード", type="primary")
        with col2:
            st.write("")

        if run_btn:
            # 一時ファイルへ保存
            in_suffix = os.path.splitext(st.session_state.upload_name)[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as tmp_in:
                tmp_in.write(st.session_state.upload_bytes)
                tmp_in.flush()
                in_path = tmp_in.name

            try:
                # 遅延インポート：モジュールが壊れていてもアプリは落ちない
                from ms_vocal_attenuator import run_file as _run_file
            except Exception as e:
                st.error(f"処理モジュールの読み込みに失敗しました: {e}")
                try:
                    os.unlink(in_path)
                except Exception:
                    pass
            else:
                try:
                    result = _run_file(in_path)  # path でも (path, stats) でもOK
                    out_path = result[0] if isinstance(result, tuple) else result

                    # ダウンロードボタン
                    file_name = os.path.basename(out_path) or f"output{os.path.splitext(in_suffix)[1]}"
                    mime = "audio/wav" if out_path.lower().endswith(".wav") else "application/octet-stream"
                    with open(out_path, "rb") as f:
                        st.download_button("結果をダウンロード", data=f, file_name=file_name, mime=mime)
                    st.success("書き出しが完了しました。")

                except Exception as e:
                    st.error(f"処理中にエラーが発生しました: {e}")

                finally:
                    try:
                        os.unlink(in_path)
                    except Exception:
                        pass
