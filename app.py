# -*- coding: utf-8 -*-
# Harmony Booster app.py (stable)
import os, io, base64, tempfile, inspect
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Harmony Booster", page_icon="🎵", layout="centered")

# -------- Login --------
def check_password() -> bool:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if st.session_state.auth_ok:
        return True

    st.title("ハーモニーブースター ログイン")
    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("パスワード", type="password")
        ok  = st.form_submit_button("ログイン")

    if ok:
        expected = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", "hb2025"))
        if pwd == expected:
            st.session_state.auth_ok = True
            st.success("ログインしました。"); st.rerun()
        else:
            st.error("パスワードが違います。")
    return False

if not check_password():
    st.stop()

# -------- Utils --------
def guess_mime_from_name(name: str) -> str:
    ext = (os.path.splitext(name)[1] or "").lower()
    m = {
        ".wav":"audio/wav",".mp3":"audio/mpeg",".m4a":"audio/mp4",".mp4":"audio/mp4",
        ".flac":"audio/flac",".ogg":"audio/ogg",".oga":"audio/ogg",".aif":"audio/aiff",".aiff":"audio/aiff",
    }
    return m.get(ext, "audio/wav")

def init_state():
    s = st.session_state
    s.setdefault("upload_name", None)
    s.setdefault("upload_bytes", None)
    s.setdefault("upload_mime",  None)

    # presets
    s.setdefault("preset_id", "male")            # male / female / custom
    s.setdefault("_last_applied_preset", None)

    # server params (export用の既定)
    s.setdefault("band_low", 200.0)
    s.setdefault("band_high", 6000.0)
    s.setdefault("mid_atten_db", -24.0)
    s.setdefault("side_gain_db", 0.0)
    s.setdefault("protect_low_hz", 120.0)
    s.setdefault("protect_high_hz", 8000.0)
    s.setdefault("output_gain_db", 0.0)

PRESET_ORDER  = ["male","female","custom"]
PRESET_LABELS = {"male":"男性","female":"女性","custom":"カスタム"}
PRESET_PARAMS = {
    "male":   dict(band_low=120.0,  band_high=4000.0,  mid_atten_db=-22.0, side_gain_db=0.0),
    "female": dict(band_low=200.0,  band_high=10000.0, mid_atten_db=-24.0, side_gain_db=1.0),
}
def apply_preset(pid: str):
    p = PRESET_PARAMS.get(pid)
    if p:
        for k,v in p.items(): st.session_state[k] = float(v)

def process_now(in_bytes: bytes, in_name: str):
    in_suffix = os.path.splitext(in_name or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as f:
        f.write(in_bytes); f.flush(); in_path = f.name
    try:
        try:
            from ms_vocal_attenuator import run_file as _run_file
        except Exception as e:
            raise RuntimeError(f"処理モジュールの読み込みに失敗しました: {e}") from e

        kw = dict(
            vocal_band=(float(st.session_state.band_low), float(st.session_state.band_high)),
            mid_atten_db=float(st.session_state.mid_atten_db),
            side_gain_db=float(st.session_state.side_gain_db),
            protect_low_hz=float(st.session_state.protect_low_hz),
            protect_high_hz=float(st.session_state.protect_high_hz),
            output_gain_db=float(st.session_state.output_gain_db),
        )

        need_out = "out_path" in inspect.signature(_run_file).parameters
        out_path = None
        if need_out:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as g:
                out_path = g.name
            try: os.unlink(out_path)
            except: pass
            ret = _run_file(in_path, out_path, **kw)
            if isinstance(ret, tuple) and ret: out_path = ret[0] or out_path
            elif isinstance(ret, str) and ret: out_path = ret
        else:
            ret = _run_file(in_path, **kw)
            out_path = ret[0] if isinstance(ret, tuple) else ret

        if not out_path or not os.path.exists(out_path):
            raise RuntimeError("処理結果ファイルが見つかりません。run_file() の出力/戻り値仕様を確認してください。")

        with open(out_path, "rb") as r: out_bytes = r.read()
        return out_bytes, guess_mime_from_name(out_path), os.path.basename(out_path)
    finally:
        try: os.unlink(in_path)
        except: pass

init_state()

# -------- UI --------
st.title("🎵 ハーモニーブースター（ハモリを聴きやすく）")
with st.expander("使い方", expanded=False):
    st.markdown("1) ①ファイル  2) ②プリセット＆プレビュー  3) ③書き出し")

tabs = st.tabs(["①ファイル","②調整＆プレビュー","③書き出し"])

# ①
with tabs[0]:
    up = st.file_uploader("音源をアップロード", type=["wav","mp3","m4a","flac","ogg","aiff","aif"])
    if up:
        st.session_state.upload_name = up.name
        st.session_state.upload_bytes = up.getbuffer().tobytes()
        st.session_state.upload_mime  = guess_mime_from_name(up.name)
        st.success(f"読み込み完了: {up.name}")

# ②
with tabs[1]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        st.subheader("ボーカル帯域プリセット")
        def _fmt(k): return PRESET_LABELS[k]
        default_idx = PRESET_ORDER.index(st.session_state.preset_id)
        st.selectbox("", PRESET_ORDER, index=default_idx, format_func=_fmt, key="preset_id", label_visibility="collapsed")
        if st.session_state.preset_id != st.session_state._last_applied_preset:
            if st.session_state.preset_id in ("male","female"): apply_preset(st.session_state.preset_id)
            st.session_state._last_applied_preset = st.session_state.preset_id

        st.subheader("プレビュー")
        b64  = base64.b64encode(st.session_state.upload_bytes).decode("ascii")
        mime = st.session_state.upload_mime or guess_mime_from_name(st.session_state.upload_name or "")
        low   = float(st.session_state.band_low)
        high  = float(st.session_state.band_high)
        mid_ui  = 0.0
        side_ui = 0.0
        out_ui  = 0.0
        plow  = float(st.session_state.protect_low_hz)
        phigh = float(st.session_state.protect_high_hz)
        band_disabled_attr = "" if st.session_state.preset_id == "custom" else "disabled"

        html = """
<!DOCTYPE html>
<html lang="ja"><head>
<meta charset="utf-8"/>
<style>
body{font-family:system-ui,Segoe UI,Helvetica,Arial,sans-serif;}
.wrap{max-width:900px;margin:0 auto;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.card{padding:10px;border:1px solid #ddd;border-radius:10px;}
.range{width:100%;}
small{color:#666;}
.val{font-variant-numeric:tabular-nums;margin-left:6px;}
</style>
</head><body>
<div class="wrap">
  <div class="card">
    <audio id="player" controls preload="auto" style="width:100%"></audio>
    <small>※ 原音は足さず、中央ボーカル帯域のみ強力に減衰します。</small>
  </div>
  <div class="grid">
    <div class="card">
      <label>帯域 Low (Hz)
        <input id="low"  class="range" type="number" min="50" max="12000" step="10" value="%%LOW%%" %%BAND_DISABLE%%>
      </label><br/>
      <label>帯域 High (Hz)
        <input id="high" class="range" type="number" min="200" max="20000" step="10" value="%%HIGH%%" %%BAND_DISABLE%%>
      </label><br/>
      <label>ミッドゲイン
        <input id="mid"  class="range" type="range" min="-80" max="6" step="0.5" value="%%MID_UI%%">
        <span id="midVal" class="val">%%MID_UI%% dB</span>
      </label><br/>
      <label>サイドゲイン
        <input id="side" class="range" type="range" min="-12" max="12" step="0.5" value="%%SIDE_UI%%">
        <span id="sideVal" class="val">%%SIDE_UI%% dB</span>
      </label><br/>
      <label>出力ゲイン
        <input id="out"  class="range" type="range" min="-12" max="12" step="0.5" value="%%OUT_UI%%">
        <span id="outVal" class="val">%%OUT_UI%% dB</span>
      </label>
    </div>
    <div class="card">
      <label>低(Hz)を保護
        <input id="plow"  class="range" type="number" min="20" max="400" step="10" value="%%PROT_LO%%">
      </label><br/>
      <label>高(Hz)を保護
        <input id="phigh" class="range" type="number" min="4000" max="20000" step="100" value="%%PROT_HI%%">
      </label><br/>
      <small>※ 男性/女性プリセット時は帯域Low/Highは固定です。変更したい場合は「カスタム」を選択してください。</small>
    </div>
  </div>
</div>
<script>
(function(){
  const dataUrl = "data:__MIME__;base64,__B64__";
  const au = document.getElementById("player");
  au.src = dataUrl;

  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();
  ["play","click","pointerdown","touchstart","keydown"].forEach(ev=>{
    document.addEventListener(ev, ()=>{ if(ctx.state!=="running") ctx.resume().catch(()=>{}); }, {passive:true});
    au.addEventListener(ev, ()=>{ if(ctx.state!=="running") ctx.resume().catch(()=>{}); }, {passive:true});
  });

  const src = ctx.createMediaElementSource(au);
  const splitter = ctx.createChannelSplitter(2);
  src.connect(splitter);

  // Mid/Side
  const gLtoM = ctx.createGain(); gLtoM.gain.value = 0.5;
  const gRtoM = ctx.createGain(); gRtoM.gain.value = 0.5;
  splitter.connect(gLtoM,0); splitter.connect(gRtoM,1);
  const mSum = ctx.createGain(); gLtoM.connect(mSum); gRtoM.connect(mSum);

  const gLtoS = ctx.createGain(); gLtoS.gain.value = 0.5;
  const gRtoS = ctx.createGain(); gRtoS.gain.value = -0.5;
  splitter.connect(gLtoS,0); splitter.connect(gRtoS,1);
  const sSum = ctx.createGain(); gLtoS.connect(sSum); gRtoS.connect(sSum);

  function clamp(x,lo,hi){ return Math.max(lo, Math.min(hi,x)); }
  function db2lin(db){ return Math.pow(10, db/20); }

  // Mid 三分割
  const lpLow1  = ctx.createBiquadFilter(); lpLow1.type="lowpass";  lpLow1.Q.value=0.707;
  const lpLow2  = ctx.createBiquadFilter(); lpLow2.type="lowpass";  lpLow2.Q.value=0.707;
  const hpBand1 = ctx.createBiquadFilter(); hpBand1.type="highpass";hpBand1.Q.value=0.707;
  const hpBand2 = ctx.createBiquadFilter(); hpBand2.type="highpass";hpBand2.Q.value=0.707;
  const lpBand1 = ctx.createBiquadFilter(); lpBand1.type="lowpass"; lpBand1.Q.value=0.707;
  const lpBand2 = ctx.createBiquadFilter(); lpBand2.type="lowpass"; lpBand2.Q.value=0.707;
  const hpHigh1 = ctx.createBiquadFilter(); hpHigh1.type="highpass";hpHigh1.Q.value=0.707;
  const hpHigh2 = ctx.createBiquadFilter(); hpHigh2.type="highpass";hpHigh2.Q.value=0.707;

  const mLow  = ctx.createGain();  mSum.connect(lpLow1); lpLow1.connect(lpLow2); lpLow2.connect(mLow);
  const mBand = ctx.createGain();  mSum.connect(hpBand1); hpBand1.connect(hpBand2); hpBand2.connect(lpBand1); lpBand1.connect(lpBand2); lpBand2.connect(mBand);
  const mHigh = ctx.createGain();  mSum.connect(hpHigh1); hpHigh1.connect(hpHigh2); hpHigh2.connect(mHigh);

  const mScaled = ctx.createGain(); mBand.connect(mScaled);
  const sumM = ctx.createGain(); mLow.connect(sumM); mScaled.connect(sumM); mHigh.connect(sumM);
  const mOut = sumM;

  // Side
  const sGain = ctx.createGain(); sGain.gain.value = 1.0; sSum.connect(sGain);

  // 合成
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
  sumL.connect(merger,0,0); sumR.connect(merger,0,1);
  merger.connect(outGain); outGain.connect(ctx.destination);

  const midVal=document.getElementById("midVal");
  const sideVal=document.getElementById("sideVal");
  const outVal=document.getElementById("outVal");

  function update(){
    try{
      let low  = parseFloat(document.getElementById("low").value)||200;
      let high = parseFloat(document.getElementById("high").value)||6000;
      let pl   = parseFloat(document.getElementById("plow").value)||120;
      let ph   = parseFloat(document.getElementById("phigh").value)||8000;

      pl = clamp(pl,10,1000); ph = clamp(ph,2000,20000);
      if (ph <= pl+10) ph = pl+10;
      low = Math.max(low,pl); high = Math.min(high,ph);
      if (high <= low+1) high = low+1;

      lpLow1.frequency.value = pl;  lpLow2.frequency.value = pl;
      hpBand1.frequency.value = low; hpBand2.frequency.value = low;
      lpBand1.frequency.value = high; lpBand2.frequency.value = high;
      hpHigh1.frequency.value = ph; hpHigh2.frequency.value = ph;

      const md = parseFloat(document.getElementById("mid").value)||0;
      const sd = parseFloat(document.getElementById("side").value)||0;
      const od = parseFloat(document.getElementById("out").value)||0;

      mScaled.gain.setTargetAtTime(Math.pow(10,md/20), ctx.currentTime, 0.01);
      sGain.gain.setTargetAtTime(Math.pow(10,sd/20), ctx.currentTime, 0.01);
      outGain.gain.setTargetAtTime(Math.pow(10,od/20), ctx.currentTime, 0.01);

      midVal.textContent  = (Math.round(md*10)/10).toFixed(1)+" dB";
      sideVal.textContent = (Math.round(sd*10)/10).toFixed(1)+" dB";
      outVal.textContent  = (Math.round(od*10)/10).toFixed(1)+" dB";
    }catch(e){}
  }
  ["low","high","mid","side","out","plow","phigh"].forEach(id=>{
    const el=document.getElementById(id);
    el.addEventListener("input",update); el.addEventListener("change",update);
  });
  update();
})();
</script>
</body></html>
        """.replace("__MIME__", mime).replace("__B64__", b64)\
           .replace("%%LOW%%", f"{low:.1f}").replace("%%HIGH%%", f"{high:.1f}")\
           .replace("%%MID_UI%%", f"{mid_ui:.1f}").replace("%%SIDE_UI%%", f"{side_ui:.1f}")\
           .replace("%%OUT_UI%%", f"{out_ui:.1f}").replace("%%PROT_LO%%", f"{plow:.1f}")\
           .replace("%%PROT_HI%%", f"{phigh:.1f}").replace("%%BAND_DISABLE%%", band_disabled_attr)

        components.html(html, height=520, scrolling=False)

# ③
with tabs[2]:
    if st.session_state.upload_bytes is None:
        st.info("先に「①ファイル」で音声を選んでください。")
    else:
        st.write(
            "現在のサーバ処理用設定："
            f"Preset {PRESET_LABELS[st.session_state.preset_id]} / "
            f"Band {st.session_state.band_low:.0f}-{st.session_state.band_high:.0f} Hz / "
            f"Mid {st.session_state.mid_atten_db:.1f} dB / Side {st.session_state.side_gain_db:.1f} dB / "
            f"Protect {st.session_state.protect_low_hz:.0f}-{st.session_state.protect_high_hz:.0f} Hz / "
            f"Out {st.session_state.output_gain_db:.1f} dB"
        )
        if st.button("高品質で処理してダウンロード", type="primary"):
            try:
                with st.spinner("書き出し中..."):
                    out_b, out_mime, out_name = process_now(st.session_state.upload_bytes, st.session_state.upload_name)
                st.download_button("結果をダウンロード", data=io.BytesIO(out_b), file_name=out_name, mime=out_mime)
                st.success("書き出しが完了しました。")
            except Exception as e:
                st.error(str(e))
