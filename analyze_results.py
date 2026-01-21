#!/usr/bin/env python
"""
proxycheck.io結果JSONをCSV統計に変換
"""
import json
import csv
import sys
from datetime import datetime
from collections import Counter


def analyze_json(json_file, csv_file):
    """
    JSON結果を読み込んでCSV統計を作成
    """
    # JSON読み込み
    print(f"Loading {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data.get('metadata', {})
    results = data.get('results', {})

    print(f"✓ Loaded {len(results)} results")

    # 統計データ収集
    stats = []
    countries = Counter()
    proxy_count = 0
    vpn_count = 0
    tor_count = 0
    risk_scores = []

    for ip, result in results.items():
        if not result.get('success'):
            continue

        result_data = result.get('data', {})

        # IPデータ取得（proxycheck.io v3形式）
        ip_data = None
        for key in result_data.keys():
            if key not in ['status', 'node', 'query_time']:
                ip_data = result_data[key]
                break

        if not ip_data:
            continue

        detections = ip_data.get('detections', {})
        location = ip_data.get('location', {})
        network = ip_data.get('network', {})

        # 統計カウント
        is_proxy = detections.get('proxy', False)
        is_vpn = detections.get('vpn', False)
        is_tor = detections.get('tor', False)
        risk = detections.get('risk', 0)

        if is_proxy:
            proxy_count += 1
        if is_vpn:
            vpn_count += 1
        if is_tor:
            tor_count += 1

        risk_scores.append(risk)
        country = location.get('country_name', 'Unknown')
        countries[country] += 1

        # 詳細データ
        stats.append({
            'IP': ip,
            'Country': country,
            'Country_Code': location.get('country_code', ''),
            'Region': location.get('region_name', ''),
            'City': location.get('city_name', ''),
            'ISP': network.get('provider', ''),
            'Organization': network.get('organisation', ''),
            'ASN': network.get('asn', ''),
            'Proxy': 'Yes' if is_proxy else 'No',
            'VPN': 'Yes' if is_vpn else 'No',
            'Tor': 'Yes' if is_tor else 'No',
            'Risk_Score': risk,
            'Type': network.get('type', ''),
            'Latitude': location.get('latitude', ''),
            'Longitude': location.get('longitude', ''),
            'Timezone': location.get('timezone', ''),
            'Checked_At': result.get('checked_at', '')
        })

    # CSV保存
    print(f"Writing to {csv_file}...")

    if stats:
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=stats[0].keys())
            writer.writeheader()
            writer.writerows(stats)

        print(f"✅ CSV saved: {csv_file}")
    else:
        print("⚠️ No data to write")
        return

    # サマリー表示
    total = len(stats)
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

    print(f"\n{'=' * 70}")
    print(f"STATISTICS SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total IPs analyzed: {total}")
    print(f"\nDetections:")
    print(f"  Proxy detected: {proxy_count} ({proxy_count/total*100:.1f}%)")
    print(f"  VPN detected: {vpn_count} ({vpn_count/total*100:.1f}%)")
    print(f"  Tor detected: {tor_count} ({tor_count/total*100:.1f}%)")

    print(f"\nRisk Scores:")
    print(f"  Average: {avg_risk:.2f}")
    print(f"  Min: {min(risk_scores) if risk_scores else 0}")
    print(f"  Max: {max(risk_scores) if risk_scores else 0}")

    print(f"\nTop 10 Countries:")
    for country, count in countries.most_common(10):
        print(f"  {country}: {count} ({count/total*100:.1f}%)")

    print(f"\n{'=' * 70}")

    # サマリーCSVも作成
    summary_file = csv_file.replace('.csv', '_summary.csv')
    print(f"\nCreating summary CSV: {summary_file}")

    summary_data = [
        {'Metric': 'Total IPs', 'Value': total},
        {'Metric': 'Proxy Count', 'Value': proxy_count},
        {'Metric': 'Proxy Percentage', 'Value': f"{proxy_count/total*100:.1f}%"},
        {'Metric': 'VPN Count', 'Value': vpn_count},
        {'Metric': 'VPN Percentage', 'Value': f"{vpn_count/total*100:.1f}%"},
        {'Metric': 'Tor Count', 'Value': tor_count},
        {'Metric': 'Tor Percentage', 'Value': f"{tor_count/total*100:.1f}%"},
        {'Metric': 'Average Risk Score', 'Value': f"{avg_risk:.2f}"},
        {'Metric': 'Min Risk Score', 'Value': min(risk_scores) if risk_scores else 0},
        {'Metric': 'Max Risk Score', 'Value': max(risk_scores) if risk_scores else 0},
    ]

    with open(summary_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['Metric', 'Value'])
        writer.writeheader()
        writer.writerows(summary_data)

    print(f"✅ Summary CSV saved: {summary_file}")

    # 国別CSVも作成
    countries_file = csv_file.replace('.csv', '_countries.csv')
    print(f"Creating countries CSV: {countries_file}")

    countries_data = [
        {'Country': country, 'Count': count, 'Percentage': f"{count/total*100:.1f}%"}
        for country, count in countries.most_common()
    ]

    with open(countries_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['Country', 'Count', 'Percentage'])
        writer.writeheader()
        writer.writerows(countries_data)

    print(f"✅ Countries CSV saved: {countries_file}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <proxycheck_json> [output_csv]")
        print("Example: python analyze_results.py proxycheck_results.json stats.csv")
        sys.exit(1)

    json_file = sys.argv[1]
    csv_file = sys.argv[2] if len(sys.argv) > 2 else 'proxycheck_stats.csv'

    print(f"{'=' * 70}")
    print(f"proxycheck.io Results Analyzer")
    print(f"{'=' * 70}")
    print(f"Input: {json_file}")
    print(f"Output: {csv_file}")
    print(f"{'=' * 70}\n")

    try:
        analyze_json(json_file, csv_file)
    except FileNotFoundError:
        print(f"❌ Error: File '{json_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
