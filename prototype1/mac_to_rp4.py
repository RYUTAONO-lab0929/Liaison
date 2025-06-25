#!/usr/bin/env python3

import subprocess
import time
import asyncio
import re
import os
from bleak import BleakScanner

# Mac側のHTTPサーバURL
MP3_URL = "http://100.64.1.13:8000/art01.mp3"

# ダウンロード先のパス (Raspberry Pi上のパス)
LOCAL_MP3_FILE = "/home/pi/art01.mp3"

# MacのBluetoothアドレス (必ず変更してください)
MAC_BT_ADDRESS = "1C:57:DC:45:07:33"  # MacのBTアドレス

# RSSIしきい値 (環境に合わせて調整が必要)
BLE_RSSI_THRESHOLD = -70      # 近距離判定 (再生開始)
BLE_RSSI_THRESHOLD_FAR = -85  # 遠距離判定 (再生停止)

# スキャンのタイムアウト時間 (秒)
SCAN_TIMEOUT = 3.0

async def get_ble_rssi():
    """
    Bleakを使ってMacのRSSIを取得
    取得できなければ-999を返す
    """
    try:
        devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)

        for dev in devices:
            if dev.address.lower() == MAC_BT_ADDRESS.lower():
                print(f"Found Mac device: {dev.address} with RSSI: {dev.rssi}")
                return dev.rssi

        print(f"Mac device with address {MAC_BT_ADDRESS} not found in scan")
    except Exception as e:
        print(f"Error scanning for BLE devices: {e}")

    return -999  # デバイスが見つからない場合

def download_mp3():
    """
    mp3ファイルをHTTPでダウンロードする。
    同じファイル名が存在する場合は上書きする。
    """
    # 既存ファイルがあれば削除（古いファイルのままになるのを防止）
    if os.path.exists(LOCAL_MP3_FILE):
        os.remove(LOCAL_MP3_FILE)

    # wgetコマンドなどでダウンロード
    print("Downloading MP3 from", MP3_URL)
    subprocess.run(["wget", "-O", LOCAL_MP3_FILE, MP3_URL])

def play_mp3():
    """
    mp3ファイルをvlcで再生。
    音声出力とボリュームを明示的に指定。
    """
    print("Playing MP3:", LOCAL_MP3_FILE)
    try:
        subprocess.Popen([
            "cvlc",
            "--play-and-exit",
            "--quiet",
            "--aout=alsa",
            "--alsa-audio-device=default",
            "--gain=1",
            LOCAL_MP3_FILE
        ])
    except Exception as e:
        print(f"Error starting VLC: {e}")

def stop_mp3():
    """
    vlcを強制終了(停止)
    """
    subprocess.run(["pkill", "vlc"])
    print("Stopped MP3 playback")

async def main_loop():
    is_playing = False
    consecutive_fails = 0  # 連続して見つからなかった回数

    print(f"Starting BLE RSSI monitoring for device: {MAC_BT_ADDRESS}")
    print(f"Near threshold: {BLE_RSSI_THRESHOLD}, Far threshold: {BLE_RSSI_THRESHOLD_FAR}")

    while True:
        ble_rssi_value = await get_ble_rssi()

        if ble_rssi_value == -999:
            consecutive_fails += 1
            print(f"Failed to detect Mac (attempt {consecutive_fails})")

            # 5回連続で見つからない場合は遠いと判断
            if consecutive_fails >= 5 and is_playing:
                print("Device not detected for too long. Stopping playback.")
                stop_mp3()
                is_playing = False
        else:
            consecutive_fails = 0  # 検出成功したらリセット
            print(f"BLE RSSI: {ble_rssi_value} dBm, Playing: {is_playing}")

            # 状態判定と制御
            if is_playing:
                # 再生中に遠距離になったら停止
                if ble_rssi_value < BLE_RSSI_THRESHOLD_FAR:
                    print("Device is too far away. Stopping playback.")
                    stop_mp3()
                    is_playing = False
            else:
                # 再生中でなく、近距離になったら再生開始
                if ble_rssi_value > BLE_RSSI_THRESHOLD:
                    print("Device is close enough. Starting playback.")
                    download_mp3()

                    if os.path.exists(LOCAL_MP3_FILE):
                        play_mp3()
                        is_playing = True
                    else:
                        print(f"MP3 file not found after download attempt, cannot play: {LOCAL_MP3_FILE}")

        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Stopping script...")
        stop_mp3()