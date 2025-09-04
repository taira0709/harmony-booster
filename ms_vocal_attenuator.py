# ms_vocal_attenuator.py
import numpy as np
import librosa
import soundfile as sf

def run_file(in_path, out_path,
             n_fft=2048,
             vocal_band=(120.0, 6000.0),
             mid_atten_db=-12.0,
             side_gain_db=0.0,
             protect_low_hz=120.0,
             protect_high_hz=8000.0,
             output_gain_db=0.0):

    # 音声を読み込み
    y, sr = librosa.load(in_path, sr=None, mono=False)
    if y.ndim == 1:
        y = np.vstack([y, y])  # モノラル→ステレオ化

    # Mid/Side 変換
    mid = (y[0] + y[1]) / 2.0
    side = (y[0] - y[1]) / 2.0

    # 周波数領域に変換
    S_mid = librosa.stft(mid, n_fft=n_fft)
    S_side = librosa.stft(side, n_fft=n_fft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # ボーカル帯域のマスクを作成
    mask = (freqs >= vocal_band[0]) & (freqs <= vocal_band[1])

    # Mid減衰
    att = 10.0 ** (mid_atten_db / 20.0)
    S_mid[mask, :] *= att

    # Side強調
    gain = 10.0 ** (side_gain_db / 20.0)
    S_side *= gain

    # 再構成
    mid = librosa.istft(S_mid)
    side = librosa.istft(S_side)

    left = mid + side
    right = mid - side
    y_out = np.vstack([left, right])

    # 出力ゲイン
    out_gain = 10.0 ** (output_gain_db / 20.0)
    y_out *= out_gain

    # ファイルに保存
    sf.write(out_path, y_out.T, sr)

    # デバッグ情報を返す
    stats = {
        "sr": sr,
        "rmsM_in": float(np.sqrt(np.mean(mid**2))),
        "rmsS_in": float(np.sqrt(np.mean(side**2))),
        "rmsM_out": float(np.sqrt(np.mean(left**2))),
        "rmsS_out": float(np.sqrt(np.mean(right**2))),
        "is_mono_like": np.allclose(y[0], y[1], atol=1e-4),
    }

    return out_path, stats
