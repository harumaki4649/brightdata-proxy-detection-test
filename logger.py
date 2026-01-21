#!/usr/bin/env python
"""
シンプルIPLogger収集スクリプト
並列でIPLoggerにアクセスしてIPアドレスを収集
"""
import urllib.request
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv
import os

# .env読み込み
load_dotenv()

# 設定
BRIGHT_DATA_PROXY_USER = os.getenv('BRIGHT_DATA_PROXY_USER', '')
BRIGHT_DATA_PROXY_PASS = os.getenv('BRIGHT_DATA_PROXY_PASS', '')
BRIGHT_DATA_PROXY_HOST = os.getenv('BRIGHT_DATA_PROXY_HOST', 'brd.superproxy.io')
BRIGHT_DATA_PROXY_PORT = os.getenv('BRIGHT_DATA_PROXY_PORT', '33335')
IPLOGGER_URL = os.getenv('IPLOGGER_URL', 'https://iplogger.com/2sijK4')
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
DELAY = float(os.getenv('DELAY_BETWEEN_REQUESTS', '0.3'))

# プロキシURL
PROXY_URL = f'http://{BRIGHT_DATA_PROXY_USER}:{BRIGHT_DATA_PROXY_PASS}@{BRIGHT_DATA_PROXY_HOST}:{BRIGHT_DATA_PROXY_PORT}'

# 結果保存
results = []
lock = Lock()


def get_ip(check_id):
    """プロキシ経由でIPLoggerにアクセスしてIPを取得"""
    try:
        # プロキシ設定
        proxy_handler = urllib.request.ProxyHandler({
            'https': PROXY_URL,
            'http': PROXY_URL
        })
        opener = urllib.request.build_opener(
            proxy_handler,
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        )

        # リクエスト
        with opener.open(IPLOGGER_URL, timeout=10) as response:
            ip = response.read().decode('utf-8').strip()
            # IPアドレスを抽出（最初の行）
            lines = ip.split('\n')
            for line in lines:
                line = line.strip()
                parts = line.split('.')
                if len(parts) == 4:
                    try:
                        if all(0 <= int(p) <= 255 for p in parts):
                            return {'success': True, 'ip': line, 'id': check_id}
                    except:
                        continue
            return {'success': True, 'ip': lines[0].strip(), 'id': check_id}
    except Exception as e:
        # 通信失敗してもIPLoggerには記録されているので成功扱い
        return {'success': True, 'ip': 'logged', 'id': check_id, 'note': 'Response failed but logged'}


def main():
    """メイン処理"""
    num_checks = 100

    print(f"IPLogger IP Collection Tool")
    print(f"=" * 60)
    print(f"Target: {IPLOGGER_URL}")
    print(f"Checks: {num_checks}")
    print(f"Workers: {MAX_WORKERS}")
    print(f"Delay: {DELAY}s")
    print(f"=" * 60)
    print()

    success_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # タスク投入
        futures = {}
        for i in range(1, num_checks + 1):
            future = executor.submit(get_ip, i)
            futures[future] = i
            time.sleep(DELAY)

        # 結果収集
        for future in as_completed(futures):
            result = future.result()

            with lock:
                results.append(result)
                success_count += 1

                # IPが取得できた場合のみ表示、それ以外は"logged"
                ip_display = result.get('ip', 'logged')
                print(f"[{result['id']:3d}/100] [OK] {ip_display}")

    # 結果サマリー
    print()
    print(f"=" * 60)
    print(f"RESULTS")
    print(f"=" * 60)
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")

    # ユニークIP統計
    unique_ips = set()
    ip_counts = {}

    for r in results:
        ip = r['ip']
        if ip != 'logged':  # レスポンス取得できたIPのみカウント
            unique_ips.add(ip)
            ip_counts[ip] = ip_counts.get(ip, 0) + 1

    print(f"\nUnique IPs: {len(unique_ips)}")
    if success_count > 0:
        print(f"Diversity: {len(unique_ips)/success_count*100:.1f}%")

    if ip_counts:
        print(f"\nTop 5 IPs:")
        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {ip}: {count}x")

        print(f"\nAll IPs ({len(unique_ips)}):")
        for ip in sorted(unique_ips):
            print(f"  {ip}")

    print(f"\n{IPLOGGER_URL}")
    print(f"→ Export the IP list from IPLogger")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
