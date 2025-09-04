# -*- coding: utf-8 -*-
# Harmony Booster app.py
# - 繧ｨ繧ｯ繧ｹ繝昴・繝・ ms_vocal_attenuator.run_file() 縺・out_path 蠢・医〒繧・荳崎ｦ√〒繧ょ虚縺上ｈ縺・↓繧｢繝繝励ヨ
# - 繝励Μ繧ｻ繝・ヨ: 蜀・Κ繧ｭ繝ｼ (male/female/custom) 縺ｧ螳牙ｮ夂ｮ｡逅・ら塙諤ｧ/螂ｳ諤ｧ縺ｯ蟶ｯ蝓・Low/High 繧堤ｷｨ髮・ｸ榊庄縲・# - 繝励Ξ繝薙Η繝ｼ: <audio controls> 陦ｨ遉ｺ繝ｻ繝溘Η繝ｼ繝医＠縺ｪ縺・・id荳牙・蜑ｲ縺ｧ荳ｭ螟ｮ繝懊・繧ｫ繝ｫ蟶ｯ蝓溘ｒ蠑ｷ蜉帶ｸ幄｡ｰ縲・# - 繧ｹ繝ｩ繧､繝繝ｼ蛻晄悄 0 dB縲∫樟蝨ｨ蛟､陦ｨ遉ｺ縲・
import os
import io
import base64
import tempfile
import inspect
import streamlit as st
import streamlit.components.v1 as components

# ========== Page ==========
st.set_page_config(page_title="Harmony Booster", page_icon="七", layout="centered")

# ========== Login ==========
def check_password() -> bool:
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if st.session_state.auth_ok:
        return True

    st.title("繝上・繝｢繝九・繝悶・繧ｹ繧ｿ繝ｼ 繝ｭ繧ｰ繧､繝ｳ")
    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("パスワード", type="password")
        ok = st.form_submit_button("繝ｭ繧ｰ繧､繝ｳ")
    if ok:
        expected = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", "hb2025"))
        if pwd == expected:
            st.session_state.auth_ok = True
            st.success("繝ｭ繧ｰ繧､繝ｳ縺励∪縺励◆縲・); st.rerun()
        else:
            st.error("繝代せ繝ｯ繝ｼ繝峨′驕輔＞縺ｾ縺吶・)
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

    # 繝励Μ繧ｻ繝・ヨ繧貞ｮ牙ｮ壹く繝ｼ縺ｧ菫晄戟
    s.setdefault("preset_id", "male")           # "male" / "female" / "custom"
    s.setdefault("_last_applied_preset", None)  # 螟画峩讀懃衍逕ｨ

    # 繧ｵ繝ｼ繝仙・逅・畑縺ｮ譌｢螳壼､・遺贈荳企Κ繝励Μ繧ｻ繝・ヨ縺ｧ譖ｴ譁ｰ・・    s.setdefault("band_low", 200.0)
    s.setdefault("band_high", 6000.0)
    s.setdefault("mid_atten_db", -24.0)  # 蠑ｷ繧√↓荳ｭ螟ｮ繝懊・繧ｫ繝ｫ貂幄｡ｰ・域嶌縺榊・縺礼畑・・    s.setdefault("side_gain_db", 0.0)
    s.setdefault("protect_low_hz", 120.0)
    s.setdefault("protect_high_hz", 8000.0)
    s.setdefault("output_gain_db", 0.0)

# 蜀・Κ繧ｭ繝ｼ 竊・陦ｨ遉ｺ繝ｩ繝吶Ν
PRESET_ORDER = ["male", "female", "custom"]
PRESET_LABELS = {"male": "逕ｷ諤ｧ", "female": "螂ｳ諤ｧ", "custom": "繧ｫ繧ｹ繧ｿ繝"}

# 逕ｷ諤ｧ/螂ｳ諤ｧ縺ｮ繝励Μ繧ｻ繝・ヨ蛟､・・ustom 縺ｯ隗ｦ繧峨↑縺・ｼ・PRESET_PARAMS = {
    "male":   dict(band_low=120.0,  band_high=4000.0,  mid_atten_db=-22.0, side_gain_db=0.0),
    "female": dict(band_low=200.0,  band_high=10000.0, mid_atten_db=-24.0, side_gain_db=1.0),
}

def apply_preset(preset_id: str):
    params = PRESET_PARAMS.get(preset_id)
    if params:
        for k, v in params.items():
            st.session_state[k] = v

def process_now(in_bytes: bytes, in_name: str):
    """竭｢譖ｸ縺榊・縺暦ｼ嗄s_vocal_attenuator.run_file 繧貞ｮ牙・縺ｫ蜻ｼ繧薙〒 bytes 繧定ｿ斐☆縲・       - out_path 蠢・育沿/荳崎ｦ∫沿縺ｩ縺｡繧峨↓繧ょｯｾ蠢懊・""
    in_suffix = os.path.splitext(in_name or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as tmp_in:
        tmp_in.write(in_bytes); tmp_in.flush()
        in_path = tmp_in.name

    try:
        try:
            from ms_vocal_attenuator import run_file as _run_file
        except Exception as e:
            raise RuntimeError(f"蜃ｦ逅・Δ繧ｸ繝･繝ｼ繝ｫ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆: {e}") from e

        kw = dict(
            vocal_band=(float(st.session_state.band_low), float(st.session_state.band_high)),
            mid_atten_db=float(st.session_state.mid_atten_db),
            side_gain_db=float(st.session_state.side_gain_db),
            protect_low_hz=float(st.session_state.protect_low_hz),
            protect_high_hz=float(st.session_state.protect_high_hz),
            output_gain_db=float(st.session_state.output_gain_db),
        )

        # 繧ｷ繧ｰ繝阪メ繝｣繧定ｦ九※ out_path 縺悟ｿ・ｦ√°蛻､譁ｭ
        need_out = "out_path" in inspect.signature(_run_file).parameters

        out_path = None
        if need_out:
            # 蜃ｺ蜉帙・ WAV 縺ｧ蜿励￠繧具ｼ医Δ繧ｸ繝･繝ｼ繝ｫ縺悟挨蠖｢蠑上〒譖ｸ縺丞ｴ蜷医・縺昴・縺ｾ縺ｾ荳頑嶌縺阪＆繧後ｋ蜑肴署・・            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_out:
                out_path = tmp_out.name
            # 荳驛ｨ螳溯｣・〒縲悟ｭ伜惠縺励※縺・ｋ縺ｨ繧ｨ繝ｩ繝ｼ縲阪↓縺ｪ繧九◆繧∝・縺ｫ豸医＠縺ｦ縺翫￥
            try: os.unlink(out_path)
            except Exception: pass

            ret = _run_file(in_path, out_path, **kw)
            # 謌ｻ繧雁､縺ｮ蠖｢縺・path / (path, 窶ｦ) / None 縺ｮ縺ｩ繧後〒繧よ鏡縺医ｋ繧医≧縺ｫ
            if isinstance(ret, tuple) and ret:
                out_path = ret[0] or out_path
            elif isinstance(ret, str) and ret:
                out_path = ret
            # ret 縺・None 縺ｧ繧・out_path 縺ｫ譖ｸ縺九ｌ縺ｦ縺・ｌ縺ｰOK
        else:
            ret = _run_file(in_path, **kw)
            out_path = ret[0] if isinstance(ret, tuple) else ret

        if not out_path or not os.path.exists(out_path):
            raise RuntimeError("蜃ｦ逅・ｵ先棡繝輔ぃ繧､繝ｫ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲Ｓun_file() 縺ｮ莉墓ｧ假ｼ域綾繧雁､/蜃ｺ蜉帛・・峨ｒ遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・)

        with open(out_path, "rb") as f:
            out_bytes = f.read()
        return out_bytes, guess_mime_from_name(out_path), os.path.basename(out_path)

    finally:
        try: os.unlink(in_path)
        except Exception: pass
        # out_path 縺ｯ蜻ｼ縺ｳ蜃ｺ縺怜・縺ｧ Bytes 縺ｫ縺励◆蠕後＾S 縺ｫ莉ｻ縺帙※OK

# 蛻晄悄蛹・init_state()

# ========== UI ==========
st.title("七 繝上・繝｢繝九・繝悶・繧ｹ繧ｿ繝ｼ・医ワ繝｢繝ｪ繧定・縺阪ｄ縺吶￥・・)
with st.expander("菴ｿ縺・婿", expanded=False):
    st.markdown(
        "1) 竭繝輔ぃ繧､繝ｫ繧帝∈縺ｶ\n"
        "2) 竭｡縺ｮ**繝懊・繧ｫ繝ｫ蟶ｯ蝓溘・繝ｪ繧ｻ繝・ヨ**・育塙諤ｧ/螂ｳ諤ｧ/繧ｫ繧ｹ繧ｿ繝・峨〒螟ｧ譫繧呈ｱｺ繧√∽ｸ九・**繝励Ξ繝薙Η繝ｼ**縺ｧ蠕ｮ隱ｿ謨ｴ\n"
        "   - 繝励Ξ繝薙Η繝ｼ縺ｯ蜃ｦ逅・浹縺ｮ縺ｿ繧堤漁縺・∪縺呻ｼ亥次髻ｳ繧定ｶｳ縺輔↑縺・粋謌撰ｼ噂n"
        "3) 竭｢譖ｸ縺榊・縺励〒竭｡荳企Κ繝励Μ繧ｻ繝・ヨ縺ｮ蛟､繧帝←逕ｨ縺励※繝繧ｦ繝ｳ繝ｭ繝ｼ繝・
    )

tabs = st.tabs(["竭繝輔ぃ繧､繝ｫ", "竭｡隱ｿ謨ｴ・・・繝ｬ繝薙Η繝ｼ", "竭｢譖ｸ縺榊・縺・])

# --- 竭 繝輔ぃ繧､繝ｫ ---
with tabs[0]:
    uploaded = st.file_uploader(
        "髻ｳ貅舌ｒ繧｢繝・・繝ｭ繝ｼ繝・,
        type=["wav","mp3","m4a","flac","ogg","aiff","aif"],
        accept_multiple_files=False,
        help="1繝輔ぃ繧､繝ｫ縺ゅ◆繧・00MB縺ｾ縺ｧ・亥ｿ・ｦ√↓蠢懊§縺ｦ螟画峩蜿ｯ・・,
    )
    if uploaded:
        st.session_state.upload_name = uploaded.name
        st.session_state.upload_bytes = uploaded.getbuffer().tobytes()
        st.session_state.upload_mime  = guess_mime_from_name(uploaded.name)
        st.success(f"隱ｭ縺ｿ霎ｼ縺ｿ螳御ｺ・ {uploaded.name}")

# --- 竭｡ 隱ｿ謨ｴ・・・繝ｬ繝薙Η繝ｼ ---
with tabs[1]:
    if st.session_state.upload_bytes is None:
        st.info("蜈医↓縲娯蔵繝輔ぃ繧､繝ｫ縲阪〒髻ｳ螢ｰ繧帝∈繧薙〒縺上□縺輔＞縲・)
    else:
        # 笆ｼ 繝励Μ繧ｻ繝・ヨ・亥・驛ｨ繧ｭ繝ｼ繧・widget 縺ｮ key 縺ｫ繧よ治逕ｨ縺励※繝悶Ξ繧呈ｹ邨ｶ・・        st.subheader("繝懊・繧ｫ繝ｫ蟶ｯ蝓溘・繝ｪ繧ｻ繝・ヨ")
        # widget 縺ｧ逶ｴ謗･ preset_id 繧堤ｮ｡逅・Ｇormat_func 縺ｧ譌･譛ｬ隱櫁｡ｨ遉ｺ縲・        default_idx = PRESET_ORDER.index(st.session_state.preset_id)
        st.selectbox(
            label="",
            options=PRESET_ORDER,
            index=default_idx,
            format_func=lambda k: PRESET_LABELS[k],
            key="preset_id",  # 竊・Widget 蛟､・昴そ繝・す繝ｧ繝ｳ縺ｮ preset_id 縺ｨ荳閾ｴ
            label_visibility="collapsed",
        )
        # 螟画峩縺後≠繧後・荳蠎ｦ縺縺鷹←逕ｨ・・ustom 縺ｯ縺昴・縺ｾ縺ｾ・・        if st.session_state.preset_id != st.session_state._last_applied_preset:
            if st.session_state.preset_id in ("male", "female"):
                apply_preset(st.session_state.preset_id)
            st.session_state._last_applied_preset = st.session_state.preset_id

        # 笆ｼ 繝励Ξ繝薙Η繝ｼ・・ebAudio繝ｻ辟｡繝溘Η繝ｼ繝茨ｼ・        st.subheader("繝励Ξ繝薙Η繝ｼ")

        b64  = base64.b64encode(st.session_state.upload_bytes).decode("ascii")
        mime = st.session_state.upload_mime or guess_mime_from_name(st.session_state.upload_name or "")

        # 繧ｹ繝ｩ繧､繝繝ｼ蛻晄悄蛟､縺ｯ 0 dB・医し繝ｼ繝仙・逅・畑縺ｨ縺ｯ迢ｬ遶具ｼ・        low   = float(st.session_state.band_low)
        high  = float(st.session_state.band_high)
        mid_ui = 0.0
        side_ui = 0.0
        out_ui = 0.0
        plow  = float(st.session_state.protect_low_hz)
        phigh = float(st.session_state.protect_high_hz)

        # 逕ｷ諤ｧ/螂ｳ諤ｧ縺ｮ縺ｨ縺阪・蟶ｯ蝓溽ｷｨ髮・ｸ榊庄
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
    <small>窶ｻ 蜴滄浹縺ｯ雜ｳ縺輔★縲∽ｸｭ螟ｮ繝懊・繧ｫ繝ｫ蟶ｯ蝓溘□縺代ｒ蠑ｷ蜉帙↓貂幄｡ｰ縺励∪縺吶・/small>
  </div>

  <div class="grid">
    <div class="card">
      <label><span>蟶ｯ蝓・Low (Hz)</span>
        <input id="low" class="range" type="number" min="50" max="12000" step="10" value="%%LOW%%" %%BAND_DISABLE%%>
      </label><br/>
      <label><span>蟶ｯ蝓・High (Hz)</span>
        <input id="high" class="range" type="number" min="200" max="20000" step="10" value="%%HIGH%%" %%BAND_DISABLE%%>
      </label><br/>

      <label><span>繝溘ャ繝峨ご繧､繝ｳ</span>
        <input id="mid" class="range" type="range" min="-80" max="6" step="0.5" value="%%MID_UI%%">
        <span id="midVal" class="val">%%MID_UI%% dB</span>
      </label><br/>
      <label><span>繧ｵ繧､繝峨ご繧､繝ｳ</span>
        <input id="side" class="range" type="range" min="-12" max="12" step="0.5" value="%%SIDE_UI%%">
        <span id="sideVal" class="val">%%SIDE_UI%% dB</span>
      </label><br/>
      <label><span>蜃ｺ蜉帙ご繧､繝ｳ</span>
        <input id="out" class="range" type="range" min="-12" max="12" step="0.5" value="%%OUT_UI%%">
        <span id="outVal" class="val">%%OUT_UI%% dB</span>
      </label>
    </div>

    <div class="card">
      <label><span>菴・Hz)繧剃ｿ晁ｭｷ</span>
        <input id="plow" class="range" type="number" min="20" max="400" step="10" value="%%PROT_LO%%">
      </label><br/>
      <label><span>鬮・Hz)繧剃ｿ晁ｭｷ</span>
        <input id="phigh" class="range" type="number" min="4000" max="20000" step="100" value="%%PROT_HI%%">
      </label><br/>
      <small>窶ｻ 逕ｷ諤ｧ/螂ｳ諤ｧ繝励Μ繧ｻ繝・ヨ譎ゅ・蟶ｯ蝓櫚ow/High縺ｯ蝗ｺ螳壹〒縺吶ょ､画峩縺励◆縺・ｴ蜷医・縲後き繧ｹ繧ｿ繝縲阪ｒ驕ｸ謚槭＠縺ｦ縺上□縺輔＞縲・/small>
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

  // 繝ｦ繝ｼ繧ｶ繝ｼ謫堺ｽ懊〒蠢・★ resume・・utoplay 蟇ｾ遲厄ｼ・  ['play','click','pointerdown','touchstart','keydown'].forEach(ev=>{
    document.addEventListener(ev, ()=>{ if (ctx.state!=='running') ctx.resume().catch(()=>{}); }, {passive:true});
    au.addEventListener(ev, ()=>{ if (ctx.state!=='running') ctx.resume().catch(()=>{}); }, {passive:true});
  });

  const src = ctx.createMediaElementSource(au);
  const splitter = ctx.createChannelSplitter(2);
  src.connect(splitter);

  // ==== Mid/Side 蛻・ｧ｣ ====
  const gLtoM = ctx.createGain(); gLtoM.gain.value = 0.5;
  const gRtoM = ctx.createGain(); gRtoM.gain.value = 0.5;
  splitter.connect(gLtoM, 0); splitter.connect(gRtoM, 1);
  const mSum = ctx.createGain(); gLtoM.connect(mSum); gRtoM.connect(mSum);

  const gLtoS = ctx.createGain(); gLtoS.gain.value = 0.5;
  const gRtoS = ctx.createGain(); gRtoS.gain.value = -0.5;
  splitter.connect(gLtoS, 0); splitter.connect(gRtoS, 1);
  const sSum = ctx.createGain(); gLtoS.connect(sSum); gRtoS.connect(sSum);

  // ==== Mid 荳牙・蜑ｲ・井ｽ・蟶ｯ蝓・鬮假ｼ俄・ 蜀榊粋謌撰ｼ亥次髻ｳ繧定ｶｳ縺輔↑縺・ｼ・===
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

  // ==== Side蜃ｦ逅・====
  const sGain = ctx.createGain(); sGain.gain.value = 1.0; sSum.connect(sGain);

  // ==== 蜃ｺ蜉帛粋謌撰ｼ・+S, M-S・・===
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

  // ==== UI・・B陦ｨ遉ｺ・・===
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

  // 繧ｹ繝ｩ繧､繝繝ｼ蛟､繧貞・譛溷喧・・渚譏
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

# --- 竭｢ 譖ｸ縺榊・縺・---
with tabs[2]:
    if st.session_state.upload_bytes is None:
        st.info("蜈医↓縲娯蔵繝輔ぃ繧､繝ｫ縲阪〒髻ｳ螢ｰ繧帝∈繧薙〒縺上□縺輔＞縲・)
    else:
        st.write("迴ｾ蝨ｨ縺ｮ繧ｵ繝ｼ繝仙・逅・畑險ｭ螳夲ｼ・
                 f"Preset {PRESET_LABELS[st.session_state.preset_id]} / "
                 f"Band {st.session_state.band_low:.0f}-{st.session_state.band_high:.0f} Hz / "
                 f"Mid {st.session_state.mid_atten_db:.1f} dB / Side {st.session_state.side_gain_db:.1f} dB / "
                 f"Protect {st.session_state.protect_low_hz:.0f}-{st.session_state.protect_high_hz:.0f} Hz / "
                 f"Out {st.session_state.output_gain_db:.1f} dB")

        if st.button("鬮伜刀雉ｪ縺ｧ蜃ｦ逅・＠縺ｦ繝繧ｦ繝ｳ繝ｭ繝ｼ繝・, type="primary"):
            try:
                with st.spinner("譖ｸ縺榊・縺嶺ｸｭ..."):
                    out_b, out_mime, out_name = process_now(
                        st.session_state.upload_bytes, st.session_state.upload_name
                    )
                st.download_button("邨先棡繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝・,
                                   data=io.BytesIO(out_b),
                                   file_name=out_name, mime=out_mime)
                st.success("譖ｸ縺榊・縺励′螳御ｺ・＠縺ｾ縺励◆縲・)
            except Exception as e:
                st.error(str(e))

