#!/usr/bin/env python
"""
IPLogger CSVからIPを抽出してproxycheck.io v3でチェック
結果をJSONで保存（レート制限対策）
"""
import urllib.request
import urllib.error
import json
import time
import ssl
import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# 設定
PROXYCHECK_API_KEY = os.getenv('PROXYCHECK_API_KEY', '')
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '3'))
DELAY = float(os.getenv('DELAY_BETWEEN_REQUESTS', '1.0'))

# 結果保存
results = {}
results_lock = Lock()
processed_count = 0
error_count = 0


def check_ip_proxycheck(ip_address, max_retries=3, retry_delay=2, verbose=False):
    """
    proxycheck.io v3でIPアドレスをチェック

    ⚠️ 重要: ローカル接続（プロキシなし）で実行
    Bright Dataプロキシは使用しない（429エラー回避のため）
    """
    # ローカル接続用のopener（プロキシなし）
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(
            context=ssl._create_unverified_context()
        )
    )

    # APIキー使用
    if PROXYCHECK_API_KEY:
        url = f"https://proxycheck.io/v3/{ip_address}?key={PROXYCHECK_API_KEY}"
    else:
        url = f"https://proxycheck.io/v3/{ip_address}"

    for attempt in range(max_retries):
        try:
            if verbose:
                print(f"  [{ip_address}] Attempt {attempt+1}/{max_retries}...")

            with opener.open(url, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                if verbose:
                    print(f"  [{ip_address}] ✓ Success")
                return {
                    'success': True,
                    'ip': ip_address,
                    'data': data,
                    'timestamp': time.time(),
                    'checked_at': datetime.now().isoformat()
                }
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                backoff_time = retry_delay * (2 ** attempt)
                print(f"  [WAIT] {ip_address} - Rate limited, waiting {backoff_time}s...")
                time.sleep(backoff_time)
            elif attempt < max_retries - 1:
                if verbose:
                    print(f"  [{ip_address}] HTTP Error {e.code}, retrying...")
                time.sleep(retry_delay)
            else:
                return {
                    'success': False,
                    'ip': ip_address,
                    'error': f'HTTP {e.code}: {e.reason}',
                    'timestamp': time.time(),
                    'checked_at': datetime.now().isoformat()
                }
        except Exception as e:
            if attempt < max_retries - 1:
                if verbose:
                    print(f"  [{ip_address}] Error: {str(e)[:50]}, retrying...")
                time.sleep(retry_delay)
            else:
                return {
                    'success': False,
                    'ip': ip_address,
                    'error': str(e),
                    'timestamp': time.time(),
                    'checked_at': datetime.now().isoformat()
                }

    return None


def load_ips_from_csv(filename):
    """
    IPLogger CSVからIPアドレスを抽出（BOM対応、タブ区切り）
    """
    ips = set()

    try:
        # BOM付きUTF-8で読み込み
        with open(filename, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

            # 1行目はsep=なのでスキップ
            if lines and lines[0].strip().startswith('sep='):
                lines = lines[1:]

            # タブ区切りで解析
            reader = csv.DictReader(lines, delimiter='\t')
            for row in reader:
                # Ip列から取得
                ip = row.get('Ip', '').strip().strip('"')

                if ip and '.' in ip:
                    # 有効なIPかチェック
                    parts = ip.split('.')
                    if len(parts) == 4:
                        try:
                            if all(0 <= int(p) <= 255 for p in parts):
                                ips.add(ip)
                        except ValueError:
                            continue

        result = sorted(list(ips))
        print(f"  Extracted {len(result)} unique IP addresses")
        return result

    except Exception as e:
        print(f"Error loading CSV: {e}")
        import traceback
        traceback.print_exc()
        return []


def save_json(data, filename):
    """
    結果をJSONで保存
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Results saved to {filename}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python proxycheck.py <iplogger_csv_file> [output_json]")
        print("Example: python proxycheck.py IPLogger-output.csv results.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'proxycheck_results.json'

    print(f"{'=' * 70}")
    print(f"proxycheck.io v3 IP Checker")
    print(f"{'=' * 70}")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"API Key: {'✓ Configured' if PROXYCHECK_API_KEY else '✗ Not configured (rate limited)'}")
    print(f"Workers: {MAX_WORKERS}")
    print(f"Delay: {DELAY}s")
    print(f"{'=' * 70}\n")

    # IPアドレス読み込み
    print("Loading IPs from CSV...")
    ips = load_ips_from_csv(input_file)

    if not ips:
        print("❌ No IPs found in CSV!")
        sys.exit(1)

    print(f"✓ Found {len(ips)} unique IP addresses\n")

    # プログレスバー用
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False
        print("Note: Install tqdm for progress bar (pip install tqdm)\n")

    # 並列チェック
    global processed_count, error_count
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        # タスク投入
        print("Submitting tasks...")
        for ip in ips:
            future = executor.submit(check_ip_proxycheck, ip)
            futures[future] = ip
            time.sleep(DELAY)

        print(f"✓ All {len(ips)} tasks submitted, processing...\n")

        # 結果収集
        if use_tqdm:
            pbar = tqdm(
                total=len(ips),
                desc="Checking IPs",
                unit="ip",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}'
            )

        for future in as_completed(futures):
            ip = futures[future]
            try:
                result = future.result()
                if result:
                    with results_lock:
                        results[ip] = result
                        if result['success']:
                            processed_count += 1
                        else:
                            error_count += 1

                    if use_tqdm:
                        # より詳細な情報を表示
                        elapsed = time.time() - start_time
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        pbar.set_postfix({
                            'OK': processed_count,
                            'NG': error_count,
                            'Current': ip[:15],
                            'Rate': f'{rate:.1f}/s'
                        })
                        pbar.update(1)
                    else:
                        status = "[OK]" if result['success'] else "[NG]"
                        elapsed = time.time() - start_time
                        print(f"{status} {ip} ({processed_count} OK, {error_count} NG) [{elapsed:.1f}s]")
            except Exception as e:
                error_count += 1
                if use_tqdm:
                    pbar.set_postfix({
                        'OK': processed_count,
                        'NG': error_count,
                        'Error': str(e)[:20]
                    })
                    pbar.update(1)
                else:
                    print(f"[ERROR] {ip}: {e}")

        if use_tqdm:
            pbar.close()

    total_time = time.time() - start_time
    print(f"\n✓ Processing completed in {total_time:.1f}s ({len(ips)/total_time:.2f} IPs/sec)")

    # 結果保存
    output_data = {
        'metadata': {
            'source_file': input_file,
            'total_ips': len(ips),
            'successful': processed_count,
            'failed': error_count,
            'generated_at': datetime.now().isoformat(),
            'api_key_used': bool(PROXYCHECK_API_KEY)
        },
        'results': results
    }

    save_json(output_data, output_file)

    # サマリー
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total IPs: {len(ips)}")
    print(f"Successful: {processed_count}")
    print(f"Failed: {error_count}")
    print(f"\nNext step:")
    print(f"  python analyze_results.py {output_file}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
