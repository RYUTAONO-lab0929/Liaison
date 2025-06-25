#!/usr/bin/env python3

import subprocess
import time
import asyncio
import re
import os
from bleak import BleakScanner
import urllib.request
import logging
from typing import Dict, Any

# ログファイルの設定
logging.basicConfig(filename='/home/pi/rp3_to_rp4.log', level=logging.INFO, format='%(asctime)s - %(message)s')
# スクリプト開始時にログを記録
logging.info('Script started')

# RP3側のHTTPサーバURL (必要に応じて変更してください)
MP3_URL = "http://100.64.1.25:8000/art01.mp3"  # RP3のIPアドレスに書き換えてください

# ダウンロード先のパス (RP4上のパス)
LOCAL_MP3_FILE = "/home/pi/music/art01.mp3"

# RP3のBluetoothアドレス (固定)
RP3_BT_ADDRESS = "B8:27:EB:6C:C6:84"

# RSSIしきい値 (環境に合わせて調整が必要)
BLE_RSSI_THRESHOLD = -40      # 近距離判定 (再生開始)
BLE_RSSI_THRESHOLD_FAR = -50  # 遠距離判定 (再生停止)

# スキャンのタイムアウト時間 (秒)
SCAN_TIMEOUT = 3.0

async def get_ble_rssi():
    """
    Bleakを使ってRP3のRSSIを取得
    取得できなければ-999を返す
    """
    try:
        devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)

        for dev in devices:
            if dev.address.lower() == RP3_BT_ADDRESS.lower():
                print(f"Found RP3 device: {dev.address} with RSSI: {dev.rssi}")
                return dev.rssi

        print(f"RP3 device with address {RP3_BT_ADDRESS} not found in scan")
    except Exception as e:
        print(f"Error scanning for BLE devices: {e}")

    return -999  # デバイスが見つからない場合

def download_mp3():
    """
    mp3ファイルをHTTPでダウンロードする。
    同じファイル名が存在する場合は上書きする。
    (urllib.requestを使用)
    """
    # 既存ファイルがあれば削除
    if os.path.exists(LOCAL_MP3_FILE):
        try:
            os.remove(LOCAL_MP3_FILE)
            print(f"Removed existing file: {LOCAL_MP3_FILE}")
        except OSError as e:
            print(f"Error removing existing file {LOCAL_MP3_FILE}: {e}")
            return False # 削除に失敗したらダウンロードに進まない

    # URLのプレースホルダーチェック
    if "<RP3_IP_ADDRESS>" in MP3_URL:
        print("Error: MP3_URLにRP3のIPアドレスが設定されていません。コードを修正してください。")
        return False

    print("Downloading MP3 from", MP3_URL, "to", LOCAL_MP3_FILE)
    try:
        # ディレクトリが存在するか確認し、なければ作成する（念のため）
        download_dir = os.path.dirname(LOCAL_MP3_FILE)
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
                print(f"Created directory: {download_dir}")
            except OSError as e:
                print(f"Error creating directory {download_dir}: {e}")
                return False

        # urllibを使ってダウンロードと保存
        urllib.request.urlretrieve(MP3_URL, LOCAL_MP3_FILE)
        print("Download completed successfully.")
        return True # ダウンロード成功

    except urllib.error.URLError as e:
        print(f"Error downloading MP3 (URL Error): {e}")
        # ダウンロードに失敗した場合、部分的に生成されたファイルを削除
        if os.path.exists(LOCAL_MP3_FILE):
            os.remove(LOCAL_MP3_FILE)
        return False
    except OSError as e:
        print(f"Error saving downloaded file (OS Error): {e}")
        # 保存時にエラーが起きても、ファイルが存在すれば削除
        if os.path.exists(LOCAL_MP3_FILE):
            os.remove(LOCAL_MP3_FILE)
        return False
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        if os.path.exists(LOCAL_MP3_FILE):
            os.remove(LOCAL_MP3_FILE)
        return False

def play_mp3():
    """
    mp3ファイルをvlcで再生。
    音声出力とボリュームを明示的に指定。
    """
    print("Playing MP3:", LOCAL_MP3_FILE)
    try:
        # 既にvlcが起動しているか確認
        result = subprocess.run(['pgrep', '-fl', 'vlc.*art01.mp3'], capture_output=True, text=True)
        if result.stdout:
            print("VLC is already playing the file.")
            return

        subprocess.Popen([
            "cvlc",
            "--play-and-exit",
            "--quiet",
            "--aout=alsa",
            "--alsa-audio-device=plughw:2,0",
            "--gain=1", # 必要であれば音量調整 (例: 0.5で半分の音量)
            LOCAL_MP3_FILE
        ])
    except FileNotFoundError:
        print("Error: 'cvlc' command not found. Please ensure VLC is installed and in your PATH.")
    except Exception as e:
        print(f"Error starting VLC: {e}")

def stop_mp3():
    """
    vlcを強制終了(停止)
    """
    print("Stopping MP3 playback...")
    try:
        # 特定のファイル名を再生しているvlcプロセスのみをkillする
        subprocess.run(["pkill", "-f", f"vlc.*{os.path.basename(LOCAL_MP3_FILE)}"])
        print("Stopped MP3 playback.")
    except FileNotFoundError:
        print("Error: 'pkill' command not found.")
    except Exception as e:
        print(f"Error stopping VLC: {e}")

async def main_loop(config: Dict[str, Any]):
    general_config = config.get('general', {})
    target_macs = config.get('target_mac_addresses', set())
    scan_interval = general_config.get('scan_interval_sec', 2.0)
    scan_timeout = general_config.get('scan_timeout_sec', 5.0) # 設定ファイルから読み込む

    logging.info("簡易テストループを開始します...")
    logging.info(f"スキャン間隔: {scan_interval}秒, スキャンタイムアウト: {scan_timeout}秒")

    while True:
        logging.debug("--- 簡易ループ開始 ---")
        # 1. Scan for beacons
        rssi_map = await get_beacon_rssi_map(target_macs, scan_timeout)
        logging.debug(f"簡易ループ: RSSIマップ = {rssi_map}")

        # (状態管理、ターゲット選択、再生/停止ロジックはすべてコメントアウト)

        # 7. Wait for next cycle (固定スリープ)
        logging.debug(f"--- 簡易ループ終了 (スリープ: {scan_interval:.2f}秒) ---")
        await asyncio.sleep(scan_interval)

if __name__ == "__main__":
    # スクリプト開始時に既存のvlcプロセスを停止する（任意）
    # stop_mp3()
    try:
        logging.info("既存の再生停止シーケンスが完了しました。")

        # --- ここから変更 ---
        # 元の main_loop 呼び出しをコメントアウト
        # asyncio.run(main_loop(config_data))

        # get_beacon_rssi_map を1回だけ呼び出すテスト関数
        async def one_shot_scan_test(config):
            logging.info("--- 1回限りのスキャンテストを開始 ---")
            target_macs = config.get('target_mac_addresses', set())
            # configからscan_timeoutを取得、失敗したらデフォルト5.0秒
            scan_timeout = config.get('general', {}).get('scan_timeout_sec', 5.0)
            logging.info(f"get_beacon_rssi_map を呼び出します (timeout={scan_timeout}, targets={target_macs})")
            # テストのためにタイムアウトを少し長めに設定 (例: 10秒)
            test_timeout = 10.0
            logging.info(f"テスト用タイムアウト: {test_timeout}秒")
            rssi_map = await get_beacon_rssi_map(target_macs, test_timeout)
            logging.info(f"1回限りのスキャンテストが終了しました。結果マップ: {rssi_map}")
            # --- 発見した全デバイス --- のログはこの関数内で出力されるはず
            logging.info("--- 1回限りのスキャンテスト完了 ---")

        # テスト関数を実行
        asyncio.run(one_shot_scan_test(config_data))
        # --- ここまで変更 ---

    except KeyboardInterrupt:
        print("Stopping script...")
        stop_mp3() # スクリプト終了時にも停止
    except Exception as e:
        print(f"An critical error occurred: {e}")
        stop_mp3() # 予期せぬエラー時も停止
