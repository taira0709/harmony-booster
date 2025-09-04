# -*- coding: utf-8 -*-
# Harmony Booster app.py
# - エクスポ�EチE ms_vocal_attenuator.run_file() ぁEout_path 忁E��でめE不要でも動くよぁE��アダプト
# - プリセチE��: 冁E��キー (male/female/custom) で安定管琁E��男性/女性は帯埁ELow/High を編雁E��可、E# - プレビュー: <audio controls> 表示・ミュートしなぁE��Eid三�E割で中央ボ�Eカル帯域を強力減衰、E# - スライダー初期 0 dB、現在値表示、E
import os
import io
import base64
import tempfile
import inspect
import streamlit as st
import streamlit.components.v1 as components

# ========== Page ==========
st.set_page_config(page_title="Harmony Booster", page_icon="🎵", layout="centered")

# ========== Login ==========
def check_password() -> bool:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if st.session_state.auth_ok:
        return True

    st.title("ハ�Eモニ�Eブ�Eスター ログイン")
    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("パスワーチE, type="password")
        ok = st.form_submit_button("ログイン")
    if ok:
        expected = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", "hb2025"))
        if pwd == expected:
            st.session_state.auth_ok = True
            st.success("ログインしました、E); st.rerun()
        else:
            st.error("パスワードが違います、E)
    return False

if not check_password():
    st.stop()

# ========== Utils ==========
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

    # プリセチE��を安定キーで保持
    s.setdefault("preset_id", "male")           # "male" / "female" / "custom"
    s.setdefault("_last_applied_preset", None)  # 変更検知用

    # サーバ�E琁E��の既定値�E�②上部プリセチE��で更新�E�E    s.setdefault("band_low", 200.0)
    s.setdefault("band_high", 6000.0)
    s.setdefault("mid_atten_db", -24.0)  # 強めに中央ボ�Eカル減衰�E�書き�Eし用�E�E    s.setdefault("side_gain_db", 0.0)
    s.setdefault("protect_low_hz", 120.0)
    s.setdefault("protect_high_hz", 8000.0)
    s.setdefault("output_gain_db", 0.0)

# 冁E��キー ↁE表示ラベル
PRESET_ORDER = ["male", "female", "custom"]
PRESET_LABELS = {"male": "男性", "female": "女性", "custom": "カスタム"}

# 男性/女性のプリセチE��値�E�Eustom は触らなぁE��EPRESET_PARAMS = {
    "male":   dict(band_low=120.0,  band_high=4000.0,  mid_atten_db=-22.0, side_gain_db=0.0),
    "female": dict(band_low=200.0,  band_high=10000.0, mid_atten_db=-24.0, side_gain_db=1.0),
}

def apply_preset(preset_id: str):
    params = PRESET_PARAMS.get(preset_id)
    if params:
        for k, v in params.items():
            st.session_state[k] = v

def process_now(in_bytes: bytes, in_name: str):
    """③書き�Eし：ms_vocal_attenuator.run_file を安�Eに呼んで bytes を返す、E       - out_path 忁E��版/不要版どちらにも対応、E""
    in_suffix = os.path.splitext(in_name or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as tmp_in:
        tmp_in.write(in_bytes); tmp_in.flush()
        in_path = tmp_in.name

    try:
        try:
            from ms_vocal_attenuator import run_file as _run_file
        except Exception as e:
            raise RuntimeError(f"処琁E��ジュールの読み込みに失敗しました: {e}") from e

        kw = dict(
            vocal_band=(float(st.session_state.band_low), float(st.session_state.band_high)),
            mid_atten_db=float(st.session_state.mid_atten_db),
            side_gain_db=float(st.session_state.side_gain_db),
            protect_low_hz=float(st.session_state.protect_low_hz),
            protect_high_hz=float(st.session_state.protect_high_hz),
            output_gain_db=float(st.session_state.output_gain_db),
        )

        # シグネチャを見て out_path が忁E��か判断
        need_out = "out_path" in inspect.signature(_run_file).parameters

        out_path = None
        if need_out:
            # 出力�E WAV で受ける（モジュールが別形式で書く場合�Eそ�Eまま上書きされる前提�E�E            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_out:
                out_path = tmp_out.name
            # 一部実裁E��「存在してぁE��とエラー」になるため�Eに消しておく
            try: os.unlink(out_path)
            except Exception: pass

            ret = _run_file(in_path, out_path, **kw)
            # 戻り値の形ぁEpath / (path, …) / None のどれでも拾えるように
            if isinstance(ret, tuple) and ret:
                out_path = ret[0] or out_path
            elif isinstance(ret, str) and ret:
                out_path = ret
            # ret ぁENone でめEout_path に書かれてぁE��ばOK
        else:
            ret = _run_file(in_path, **kw)
            out_path = ret[0] if isinstance(ret, tuple) else ret

        if not out_path or not os.path.exists(out_path):
            raise RuntimeError("処琁E��果ファイルが見つかりません。run_file() の仕様（戻り値/出力�E�E�を確認してください、E)

        with open(out_path, "rb") as f:
            out_bytes = f.read()
        return out_bytes, guess_mime_from_name(out_path), os.path.basename(out_path)

    finally:
        try: os.unlink(in_path)
        except Exception: pass
        # out_path は呼び出し�Eで Bytes にした後、OS に任せてOK

# 初期匁Einit_state()

# ========== UI ==========
st.title("🎵 ハ�Eモニ�Eブ�Eスター�E�ハモリを�Eきやすく�E�E)
with st.expander("使ぁE��", expanded=False):
    st.markdown(
        "1) ①ファイルを選ぶ\n"
        "2) ②の**ボ�Eカル帯域�EリセチE��**�E�男性/女性/カスタム�E�で大枠を決め、下�E**プレビュー**で微調整\n"
        "   - プレビューは処琁E��のみを狙ぁE��す（原音を足さなぁE��成）\n"
        "3) ③書き�Eしで②上部プリセチE��の値を適用してダウンローチE
    )

tabs = st.tabs(["①ファイル", "②調整�E�E�Eレビュー", "③書き�EぁE])

# --- ① ファイル ---
with tabs[0]:
    uploaded = st.file_uploader(
        "音源をアチE�EローチE,
        type=["wav","mp3","m4a","flac","ogg","aiff","aif"],
        accept_multiple_files=False,
        help="1ファイルあためE00MBまで�E�忁E��に応じて変更可�E�E,
    )
    if uploaded:
        st.session_state.upload_name = uploaded.name
        st.session_state.upload_bytes = uploaded.getbuffer().tobytes()
        st.session_state.upload_mime  = guess_mime_from_name(uploaded.name)
        st.success(f"読み込み完亁E {uploaded.name}")

# --- ② 調整�E�E�Eレビュー ---
with tabs[1]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください、E)
    else:
        # ▼ プリセチE���E��E部キーめEwidget の key にも採用してブレを根絶�E�E        st.subheader("ボ�Eカル帯域�EリセチE��")
        # widget で直接 preset_id を管琁E��format_func で日本語表示、E        default_idx = PRESET_ORDER.index(st.session_state.preset_id)
        st.selectbox(
            label="",
            options=PRESET_ORDER,
            index=default_idx,
            format_func=lambda k: PRESET_LABELS[k],
            key="preset_id",  # ↁEWidget 値�E�セチE��ョンの preset_id と一致
            label_visibility="collapsed",
        )
        # 変更があれ�E一度だけ適用�E�Eustom はそ�Eまま�E�E        if st.session_state.preset_id != st.session_state._last_applied_preset:
            if st.session_state.preset_id in ("male", "female"):
                apply_preset(st.session_state.preset_id)
            st.session_state._last_applied_preset = st.session_state.preset_id

        # ▼ プレビュー�E�EebAudio・無ミュート！E        st.subheader("プレビュー")

        b64  = base64.b64encode(st.session_state.upload_bytes).decode("ascii")
        mime = st.session_state.upload_mime or guess_mime_from_name(st.session_state.upload_name or "")

        # スライダー初期値は 0 dB�E�サーバ�E琁E��とは独立！E        low   = float(st.session_state.band_low)
        high  = float(st.session_state.band_high)
        mid_ui = 0.0
        side_ui = 0.0
        out_ui = 0.0
        plow  = float(st.session_state.protect_low_hz)
        phigh = float(st.session_state.protect_high_hz)

        # 男性/女性のとき�E帯域編雁E��可
        band_disabled_attr = "" if st.session_state.preset_id == "custom" else "disabled"

        html = """
<!DOCTYPE html>
<html lang="ja"><head>
<meta charset="utf-8" />
<style>
body { font-family: system-ui, Segoe UI, Helvetica, Arial, sans-serif; }
.wrap { max-width: 900px; margin: 0 auto; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { padding: 10px; border: 1px solid #ddd; border-radius: 10px; }
label span { display:inline-block; width: 160px; }
.range { width: 100%; }
small { color:#666; }
.val { font-variant-numeric: tabular-nums; margin-left: 6px; }
</style>
</head><body>
<div class="wrap">
  <div class="card">
    <audio id="player" controls preload="auto" style="width:100%"></audio>
    <small>※ 原音は足さず、中央ボ�Eカル帯域だけを強力に減衰します、E/small>
  </div>

  <div class="grid">
    <div class="card">
      <label><span>帯埁ELow (Hz)</span>
        <input id="low" class="range" type="number" min="50" max="12000" step="10" value="%%LOW%%" %%BAND_DISABLE%%>
      </label><br/>
      <label><span>帯埁EHigh (Hz)</span>
        <input id="high" class="range" type="number" min="200" max="20000" step="10" value="%%HIGH%%" %%BAND_DISABLE%%>
      </label><br/>

      <label><span>ミッドゲイン</span>
        <input id="mid" class="range" type="range" min="-80" max="6" step="0.5" value="%%MID_UI%%">
        <span id="midVal" class="val">%%MID_UI%% dB</span>
      </label><br/>
      <label><span>サイドゲイン</span>
        <input id="side" class="range" type="range" min="-12" max="12" step="0.5" value="%%SIDE_UI%%">
        <span id="sideVal" class="val">%%SIDE_UI%% dB</span>
      </label><br/>
      <label><span>出力ゲイン</span>
        <input id="out" class="range" type="range" min="-12" max="12" step="0.5" value="%%OUT_UI%%">
        <span id="outVal" class="val">%%OUT_UI%% dB</span>
      </label>
    </div>

    <div class="card">
      <label><span>佁EHz)を保護</span>
        <input id="plow" class="range" type="number" min="20" max="400" step="10" value="%%PROT_LO%%">
      </label><br/>
      <label><span>髁EHz)を保護</span>
        <input id="phigh" class="range" type="number" min="4000" max="20000" step="100" value="%%PROT_HI%%">
      </label><br/>
      <small>※ 男性/女性プリセチE��時�E帯域Low/Highは固定です。変更したぁE��合�E「カスタム」を選択してください、E/small>
    </div>
  </div>
</div>

<script>
(function(){
  const dataUrl = "data:__MIME__;base64,__B64__";
  const au = document.getElementById('player');
  au.src = dataUrl;

  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();

  // ユーザー操作で忁E�� resume�E�Eutoplay 対策！E  ['play','click','pointerdown','touchstart','keydown'].forEach(ev=>{
    document.addEventListener(ev, ()=>{ if (ctx.state!=='running') ctx.resume().catch(()=>{}); }, {passive:true});
    au.addEventListener(ev, ()=>{ if (ctx.state!=='running') ctx.resume().catch(()=>{}); }, {passive:true});
  });

  const src = ctx.createMediaElementSource(au);
  const splitter = ctx.createChannelSplitter(2);
  src.connect(splitter);

  // ==== Mid/Side 刁E�� ====
  const gLtoM = ctx.createGain(); gLtoM.gain.value = 0.5;
  const gRtoM = ctx.createGain(); gRtoM.gain.value = 0.5;
  splitter.connect(gLtoM, 0); splitter.connect(gRtoM, 1);
  const mSum = ctx.createGain(); gLtoM.connect(mSum); gRtoM.connect(mSum);

  const gLtoS = ctx.createGain(); gLtoS.gain.value = 0.5;
  const gRtoS = ctx.createGain(); gRtoS.gain.value = -0.5;
  splitter.connect(gLtoS, 0); splitter.connect(gRtoS, 1);
  const sSum = ctx.createGain(); gLtoS.connect(sSum); gRtoS.connect(sSum);

  // ==== Mid 三�E割�E�佁E帯埁E高）�E 再合成（原音を足さなぁE��E===
  function clamp(x, lo, hi){ return Math.max(lo, Math.min(hi, x)); }
  function db2lin(db){ return Math.pow(10, db/20); }

  const lpLow1 = ctx.createBiquadFilter(); lpLow1.type='lowpass'; lpLow1.Q.value=0.707;
  const lpLow2 = ctx.createBiquadFilter(); lpLow2.type='lowpass'; lpLow2.Q.value=0.707;

  const hpBand1 = ctx.createBiquadFilter(); hpBand1.type='highpass'; hpBand1.Q.value=0.707;
  const hpBand2 = ctx.createBiquadFilter(); hpBand2.type='highpass'; hpBand2.Q.value=0.707;
  const lpBand1 = ctx.createBiquadFilter(); lpBand1.type='lowpass';  lpBand1.Q.value=0.707;
  const lpBand2 = ctx.createBiquadFilter(); lpBand2.type='lowpass';  lpBand2.Q.value=0.707;

  const hpHigh1 = ctx.createBiquadFilter(); hpHigh1.type='highpass'; hpHigh1.Q.value=0.707;
  const hpHigh2 = ctx.createBiquadFilter(); hpHigh2.type='highpass'; hpHigh2.Q.value=0.707;

  const mLow  = ctx.createGain();  mSum.connect(lpLow1); lpLow1.connect(lpLow2); lpLow2.connect(mLow);
  const mBand = ctx.createGain();  mSum.connect(hpBand1); hpBand1.connect(hpBand2); hpBand2.connect(lpBand1); lpBand1.connect(lpBand2); lpBand2.connect(mBand);
  const mHigh = ctx.createGain();  mSum.connect(hpHigh1); hpHigh1.connect(hpHigh2); hpHigh2.connect(mHigh);

  const mScaled = ctx.createGain(); mBand.connect(mScaled);
  const sumM = ctx.createGain(); mLow.connect(sumM); mScaled.connect(sumM); mHigh.connect(sumM);
  const mOut = sumM;

  // ==== Side処琁E====
  const sGain = ctx.createGain(); sGain.gain.value = 1.0; sSum.connect(sGain);

  // ==== 出力合成！E+S, M-S�E�E===
  const sumL = ctx.createGain(); const sumR = ctx.createGain();
  const mToL = ctx.createGain(); mToL.gain.value = 1.0;
  const sToL = ctx.createGain(); sToL.gain.value = 1.0;
  const mToR = ctx.createGain(); mToR.gain.value = 1.0;
  const sToR = ctx.createGain(); sToR.gain.value = -1.0;
  mOut.connect(mToL); sGain.connect(sToL);
  mOut.connect(mToR); sGain.connect(sToR);
  mToL.connect(sumL); sToL.connect(sumL);
  mToR.connect(sumR); sToR.connect(sumR);

  const outGain = ctx.createGain(); outGain.gain.value = 1.0;
  const merger = ctx.createChannelMerger(2);
  sumL.connect(merger, 0, 0);
  sumR.connect(merger, 0, 1);
  merger.connect(outGain);
  outGain.connect(ctx.destination);

  // ==== UI�E�EB表示�E�E===
  const midVal  = document.getElementById('midVal');
  const sideVal = document.getElementById('sideVal');
  const outVal  = document.getElementById('outVal');

  function update(){
    try{
      let low  = parseFloat(document.getElementById('low').value)||200;
      let high = parseFloat(document.getElementById('high').value)||6000;
      let pl   = parseFloat(document.getElementById('plow').value)||120;
      let ph   = parseFloat(document.getElementById('phigh').value)||8000;

      pl = clamp(pl, 10, 1000);
      ph = clamp(ph, 2000, 20000);
      if (ph <= pl + 10) ph = pl + 10;
      low  = Math.max(low,  pl);
      high = Math.min(high, ph);
      if (high <= low + 1) high = low + 1;

      lpLow1.frequency.value = pl;   lpLow2.frequency.value = pl;
      hpBand1.frequency.value = low; hpBand2.frequency.value = low;
      lpBand1.frequency.value = high;lpBand2.frequency.value = high;
      hpHigh1.frequency.value = ph;  hpHigh2.frequency.value = ph;

      const md  = parseFloat(document.getElementById('mid').value)||0;
      const sd  = parseFloat(document.getElementById('side').value)||0;
      const od  = parseFloat(document.getElementById('out').value)||0;

      mScaled.gain.setTargetAtTime(db2lin(md), ctx.currentTime, 0.01);
      sGain.gain.setTargetAtTime(db2lin(sd), ctx.currentTime, 0.01);
      outGain.gain.setTargetAtTime(db2lin(od), ctx.currentTime, 0.01);

      midVal.textContent  = (Math.round(md*10)/10).toFixed(1) + " dB";
      sideVal.textContent = (Math.round(sd*10)/10).toFixed(1) + " dB";
      outVal.textContent  = (Math.round(od*10)/10).toFixed(1) + " dB";
    }catch(e){ console.warn("update skipped", e); }
  }

  // スライダー値を�E期化�E�E��映
  document.getElementById('low').value   = "%%LOW%%";
  document.getElementById('high').value  = "%%HIGH%%";
  document.getElementById('mid').value   = "%%MID_UI%%";
  document.getElementById('side').value  = "%%SIDE_UI%%";
  document.getElementById('out').value   = "%%OUT_UI%%";
  document.getElementById('plow').value  = "%%PROT_LO%%";
  document.getElementById('phigh').value = "%%PROT_HI%%";
  update();

  ['low','high','mid','side','out','plow','phigh'].forEach(id=>{
    const el = document.getElementById(id);
    el.addEventListener('input', update);
    el.addEventListener('change', update);
  });

  au.addEventListener('play', ()=>{ if (ctx.state!=='running'){ ctx.resume().catch(()=>{}); } });
})();
</script>
</body></html>
        """.replace("__MIME__", mime).replace("__B64__", b64)
        html = (html
                .replace("%%LOW%%", f"{low:.1f}")
                .replace("%%HIGH%%", f"{high:.1f}")
                .replace("%%MID_UI%%", f"{mid_ui:.1f}")
                .replace("%%SIDE_UI%%", f"{side_ui:.1f}")
                .replace("%%OUT_UI%%", f"{out_ui:.1f}")
                .replace("%%PROT_LO%%", f"{plow:.1f}")
                .replace("%%PROT_HI%%", f"{phigh:.1f}")
                .replace("%%BAND_DISABLE%%", band_disabled_attr)
                )
        components.html(html, height=520, scrolling=False)

# --- ③ 書き�EぁE---
with tabs[2]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください、E)
    else:
        st.write("現在のサーバ�E琁E��設定！E
                 f"Preset {PRESET_LABELS[st.session_state.preset_id]} / "
                 f"Band {st.session_state.band_low:.0f}-{st.session_state.band_high:.0f} Hz / "
                 f"Mid {st.session_state.mid_atten_db:.1f} dB / Side {st.session_state.side_gain_db:.1f} dB / "
                 f"Protect {st.session_state.protect_low_hz:.0f}-{st.session_state.protect_high_hz:.0f} Hz / "
                 f"Out {st.session_state.output_gain_db:.1f} dB")

        if st.button("高品質で処琁E��てダウンローチE, type="primary"):
            try:
                with st.spinner("書き�Eし中..."):
                    out_b, out_mime, out_name = process_now(
                        st.session_state.upload_bytes, st.session_state.upload_name
                    )
                st.download_button("結果をダウンローチE,
                                   data=io.BytesIO(out_b),
                                   file_name=out_name, mime=out_mime)
                st.success("書き�Eしが完亁E��ました、E)
            except Exception as e:
                st.error(str(e))
