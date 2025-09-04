# -*- coding: utf-8 -*-
import os, re, base64, tempfile, contextlib
import streamlit as st
import streamlit.components.v1 as components

# ===================== ページ設定（最初の st コマンド） =====================
st.set_page_config(page_title="Harmony Booster", layout="wide")

# ===================== パスワード制限（LINE登録者専用） =====================
PASSWORD = os.environ.get("APP_PASSWORD", "hb2025")

# 互換用：古いStreamlitでも動く rerun ラッパ
def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        # 古いバージョンでは experimental_rerun
        st.experimental_rerun()

# 起動を止めないための遅延インポート（ms_vocal_attenuator が壊れていてもアプリは起動させる）
RUNFILE_IMPORT_ERROR = None
def _import_run_file():
    """ms_vocal_attenuator.run_file を必要時に読み込む。失敗してもアプリは落とさない。"""
    global RUNFILE_IMPORT_ERROR
    if RUNFILE_IMPORT_ERROR is None:
        try:
            from ms_vocal_attenuator import run_file
            return run_file
        except Exception as e:
            RUNFILE_IMPORT_ERROR = e
            return None
    # 既に失敗記録がある場合は None
    return None

# --- tabs フォールバック（古い Streamlit 向け） ---
def _tabs_safe(labels):
    """st.tabs が無い／壊れている環境でも落とさずに表示を継続する"""
    try:
        return st.tabs(labels)
    except Exception:
        st.warning("※ お使いの Streamlit ではタブUIが無効のため、簡易表示に切り替えました。")
        return tuple(st.container() for _ in labels)

# ---- 認証ブロック ----
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.header("ハーモニーブースター ログインページ")
    pw = st.text_input("パスワードを入力してください", type="password", key="login_pw")

    if pw == PASSWORD:
        st.session_state["authenticated"] = True
        st.session_state.pop("login_pw", None)  # 入力欄のクリア（任意）
        _safe_rerun()  # ここで実行を切り替える（以降の行は実行されない）

    if pw != "":
        st.warning("このアプリはLINE登録者限定です。LINEで配布されたパスワードを入力してください。")
    st.stop()  # 未認証の時はここで終了（次の入力待ち）

# ===================== テーマCSS（パキッと濃いブルー） =====================
st.markdown("""
<style>
:root { 
  --brand: #0D47A1;   /* 濃いブルー */
  --bg: #FFFFFF; 
  --bg2: #E3F2FD;     /* 明るい青系カード背景 */
  --text: #0A0A0A;    /* 黒に近い文字色 */
}

/* 全体 */
.block-container { max-width: 960px; }
section.main > div { padding: 1.2rem; background-color: var(--bg); }

/* タイトル */
h1, h2, h3 {
  color: var(--brand);
  font-weight: 700;
}

/* カード */
.card {
  background-color: var(--bg2);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.12);
}

/* ボタン */
.stButton > button {
  background-color: var(--brand) !important;
  color: #fff !important;
  border-radius: 6px !important;
  font-weight: 600 !important;
  box-shadow: 0 3px 6px rgba(0,0,0,0.2);
}
.stButton > button:hover {
  background-color: #1565C0 !important;
}

/* ラベル */
.stFileUploader label { font-weight: bold; color: var(--brand); }
.stSlider label { font-weight: 600; color: #1A237E; }
.stTextInput label { font-weight: bold; color: var(--brand); }
</style>
""", unsafe_allow_html=True)

# ===================== アプリ本体 =====================
st.title("Harmony Booster")

with st.expander("使い方（タップで開く）", expanded=False):
    st.markdown("""
    **① ファイル**をアップロード → **② プリセット**を選ぶ（カスタム可）  
    → **③ プレビュー**で調整（ミュートになっていないか確認）  
    → **④ エクスポート**でWAVを書き出し
    """)

# 先に初期化（NameError回避）
uploaded = None

# タブ（フォールバック対応）
tab1, tab2, tab3, tab4 = _tabs_safe(["① ファイル", "② プリセット", "③ プレビュー", "④ エクスポート"])

# --- タブ1: ファイル ---
with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("ファイルを選ぶ")
    uploaded = st.file_uploader("音源をアップロード", type=["wav","mp3","m4a","flac","ogg","aiff","aif"])
    if uploaded:
        st.success(f"選択中：**{uploaded.name}**")
    else:
        st.info("WAV/MP3/M4A/FLAC/OGG/AIFF に対応しています。")
    st.markdown("</div>", unsafe_allow_html=True)

# --- タブ2: プリセット ---
with tab2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("声種プリセット")
    # セッション既定を安全に初期化（重複してもOK）
    st.session_state.setdefault("lo_hz", 120)
    st.session_state.setdefault("hi_hz", 6000)

    colL, colR = st.columns([1,1])
    with colL:
        preset = st.selectbox("プリセットを選択", ["カスタム","低い男性","高い男性","低い女性","高い女性"])

    def preset_band(p):
        return {
            "低い男性": (100,4500),
            "高い男性": (120,6000),
            "低い女性": (150,6500),
            "高い女性": (200,7500)
        }.get(p, None)

    band = preset_band(preset)
    with colR:
        if band:
            lo, hi = band
            st.caption(f"帯域 {lo}-{hi} Hz が適用されます")
            st.session_state["lo_hz"], st.session_state["hi_hz"] = int(lo), int(hi)
        else:
            st.session_state["lo_hz"] = st.number_input(
                "下限Hz", min_value=20, max_value=1000,
                value=int(st.session_state.get("lo_hz",120)), step=10
            )
            st.session_state["hi_hz"] = st.number_input(
                "上限Hz", min_value=1000, max_value=20000,
                value=int(st.session_state.get("hi_hz",6000)), step=100
            )
    st.markdown("</div>", unsafe_allow_html=True)

# --- タブ3: プレビュー ---
with tab3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("ライブプレビュー")
    if uploaded:
        # data URL を生成（ここは Python 側で作ってHTMLに差し込む）
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ext == ".wav":
            mime = "audio/wav"
        elif ext in [".aif",".aiff"]:
            mime = "audio/aiff"
        elif ext == ".flac":
            mime = "audio/flac"
        elif ext in [".ogg",".oga"]:
            mime = "audio/ogg"
        elif ext in [".m4a",".mp4",".aac"]:
            mime = "audio/mp4"
        else:
            mime = "audio/mpeg"
        b64 = base64.b64encode(uploaded.getbuffer()).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"

        lo0 = int(st.session_state.get("lo_hz", 120))
        hi0 = int(st.session_state.get("hi_hz", 6000))

        # プレースホルダ方式（{DATA_URL}, __LO__, __HI__ をあとで置換）
        html = """
<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body>
  <audio id="player" controls src="{DATA_URL}" style="width:100%"></audio>
  <div style="margin-top:10px">
    <label>Mid (dB) <input id="mid" type="range" min="-30" max="0" step="0.5" value="-12" aria-label="Mid gain"></label>
    <label>Side (dB) <input id="side" type="range" min="-6" max="12" step="0.5" value="0" aria-label="Side gain"></label>
    <label>Lo (Hz) <input id="lo" type="number" value="__LO__" aria-label="Low cutoff"></label>
    <label>Hi (Hz) <input id="hi" type="number" value="__HI__" aria-label="High cutoff"></label>
    <button id="copybtn" type="button">Copy values</button>
    <span id="vals" style="margin-left:8px;font-size:13px;color:#333"></span>
  </div>

  <script>
    const audio = document.getElementById('player');
    const mid = document.getElementById('mid');
    const side = document.getElementById('side');
    const lo = document.getElementById('lo');
    const hi = document.getElementById('hi');

    let ctx=null, src=null, splitter=null, merger=null;
    let mGain=null, sGain=null, bpM=null, bpS=null;

    function db(v) { return Math.pow(10, v/20); }

    async function initGraphIfNeeded(){
      if (ctx) return;
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      src = ctx.createMediaElementSource(audio);

      splitter = ctx.createChannelSplitter(2);
      merger   = ctx.createChannelMerger(2);

      const lChan = ctx.createGain();
      const rChan = ctx.createGain();

      const lToM = ctx.createGain(); lToM.gain.value = 0.5;
      const rToM = ctx.createGain(); rToM.gain.value = 0.5;
      const lToS = ctx.createGain(); lToS.gain.value = 0.5;
      const rToS = ctx.createGain(); rToS.gain.value = -0.5;

      const sumM = ctx.createGain(); sumM.gain.value = 1.0;
      const sumS = ctx.createGain(); sumS.gain.value = 1.0;

      mGain = ctx.createGain();
      sGain = ctx.createGain();

      bpM = ctx.createBiquadFilter(); bpM.type = "bandpass";
      bpS = ctx.createBiquadFilter(); bpS.type = "bandpass";

      // wire
      src.connect(splitter);
      splitter.connect(lChan, 0);
      splitter.connect(rChan, 1);

      // Mid path
      lChan.connect(lToM); rChan.connect(rToM);
      lToM.connect(sumM);  rToM.connect(sumM);
      sumM.connect(bpM).connect(mGain);

      // Side path
      lChan.connect(lToS); rChan.connect(rToS);
      lToS.connect(sumS);  rToS.connect(sumS);
      sumS.connect(bpS).connect(sGain);

      // Re-sum（処理音のみ出力）
      const sToL = ctx.createGain(); sToL.gain.value = 1.0;
      const sToR = ctx.createGain(); sToR.gain.value = -1.0;

      mGain.connect(merger, 0, 0);
      sGain.connect(sToL); sToL.connect(merger, 0, 0);

      mGain.connect(merger, 0, 1);
      sGain.connect(sToR); sToR.connect(merger, 0, 1);

      // 出力（原音の直出しは無し）
      merger.connect(ctx.destination);

      updateAll();
    }

    function updateAll(){
      if (!mGain || !sGain || !bpM || !bpS) return;

      // gains
      mGain.gain.value = db(parseFloat(mid.value || "-12"));
      sGain.gain.value = db(parseFloat(side.value || "0"));

      // band from lo/hi -> center & Q
      const fLo = Math.max(20, parseFloat(lo.value || "120"));
      const fHi = Math.min(20000, parseFloat(hi.value || "6000"));
      const center = Math.sqrt(fLo * fHi);
      const bw = Math.max(100, fHi - fLo);
      const Q = Math.max(0.0001, center / bw);
      bpM.frequency.value = center; bpM.Q.value = Q;
      bpS.frequency.value = center; bpS.Q.value = Q;

      const txt = "mid=" + (parseFloat(mid.value)||0)
                + ", side=" + (parseFloat(side.value)||0)
                + ", lo=" + (parseFloat(lo.value)||120)
                + ", hi=" + (parseFloat(hi.value)||6000);
      const span = document.getElementById('vals');
      if (span) span.textContent = txt;
    }

    audio.onplay = async () => {
      await initGraphIfNeeded();
      if (ctx && ctx.state === "suspended") ctx.resume();
    };

    mid.oninput = updateAll;
    side.oninput = updateAll;
    lo.onchange = updateAll;
    hi.onchange = updateAll;

    document.getElementById('copybtn').onclick = async () => {
      const s = document.getElementById('vals').textContent || "";
      try {
        await navigator.clipboard.writeText(s);
        const btn = document.getElementById('copybtn');
        btn.textContent = "Copied";
        setTimeout(()=>{ btn.textContent = "Copy values"; }, 1200);
      } catch(e) {
        alert("Clipboard copy failed");
      }
    };

    updateAll();
  </script>
</body>
</html>
        """
        # プレースホルダをまとめて置換
        html = (html
                .replace("{DATA_URL}", data_url)
                .replace("__LO__", str(lo0))
                .replace("__HI__", str(hi0)))
        components.html(html, height=400)
    else:
        st.info("タブ①で音源をアップしてからプレビューしてください。")
    st.markdown("</div>", unsafe_allow_html=True)

# --- タブ4: エクスポート ---
with tab4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("エクスポート")
    vals_in = st.text_input("③の Copy values でコピーした文字列を貼り付け（例: mid=-12, side=0, lo=120, hi=6000）")

    if st.button("WAVを書き出す", disabled=not bool(uploaded)) and uploaded:
        # 遅延インポート確認（run_file を使う直前に必ず）
        run_file = _import_run_file()
        if run_file is None:
            st.error("処理モジュールの読み込みに失敗しました。ms_vocal_attenuator.py が欠落/エラーの可能性。\n\n詳細: " + str(RUNFILE_IMPORT_ERROR))
            st.stop()

        # 値をパース（無ければセッション既定を使用）
        kv = dict(re.findall(r"(mid|side|lo|hi)=([-+]?[0-9.]+)", vals_in or ""))

        def _safe_float(s, default):
            try:
                x = float(s)
                if x == x and x not in (float("inf"), float("-inf")):
                    return x
            except Exception:
                pass
            return default

        mid_db  = _safe_float(kv.get("mid"),  -12)
        side_db = _safe_float(kv.get("side"),   0)
        lo_hz   = _safe_float(kv.get("lo"),   float(st.session_state.get("lo_hz", 120)))
        hi_hz   = _safe_float(kv.get("hi"),   float(st.session_state.get("hi_hz", 6000)))

        # 範囲補正と整合性チェック
        lo_hz = max(20.0, lo_hz)
        hi_hz = min(20000.0, hi_hz)
        if lo_hz >= hi_hz:
            lo_hz, hi_hz = 120.0, 6000.0  # 既定に戻す

        # 一時ファイル作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1]) as tmp_in:
            tmp_in.write(uploaded.getbuffer()); in_path = tmp_in.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_out:
            out_path = tmp_out.name

        with st.spinner("解析中..."):
            try:
                saved, stats = run_file(
                    in_path, out_path,
                    n_fft=2048,
                    vocal_band=(lo_hz, hi_hz),
                    mid_atten_db=mid_db,
                    side_gain_db=side_db,
                    protect_low_hz=120,
                    protect_high_hz=8000,
                    output_gain_db=0
                )
                with open(saved, "rb") as f:
                    audio_bytes = f.read()
                st.success("完了。プレビューとダウンロードが可能です。")
                st.audio(audio_bytes, format="audio/wav")

                base, _ = os.path.splitext(uploaded.name)
                # mid_dbはfloatなので .is_integer() で整数表記をキレイに
                dl_mid = f"{int(mid_db)}dB" if float(mid_db).is_integer() else f"{mid_db}dB"
                dl_name = f"{base}_hb_{int(lo_hz)}-{int(hi_hz)}_{dl_mid}.wav"
                st.download_button("処理後のWAVをダウンロード", data=audio_bytes, file_name=dl_name, mime="audio/wav")

            except Exception as e:
                st.error("処理に失敗しました。ファイル形式（拡張子）やファイルの破損、もしくはパラメータ値をご確認のうえ再試行してください。\n\n詳細: " + str(e))
            finally:
                with contextlib.suppress(Exception):
                    if os.path.exists(in_path): os.unlink(in_path)
                with contextlib.suppress(Exception):
                    if os.path.exists(out_path): os.unlink(out_path)
    if not uploaded:
        st.caption("※ 先にタブ①でファイルを選ぶと有効になります。")
    st.markdown("</div>", unsafe_allow_html=True)
