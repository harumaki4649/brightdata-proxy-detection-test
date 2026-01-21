# Bright Data Proxy Detection Test

Bright Dataのプロキシがproxycheck.io（v3 API）などの検知サービスを回避できるか検証するツール

## 概要

このプロジェクトは、Bright Dataの住宅用プロキシを使用して、proxycheck.io v3 APIに対する検知回避率を統計的に検証します。

**検証結果: 475個のIPアドレス中、プロキシ検知はわずか2件（0.4%）**

詳細な分析は[Qiita記事](https://qiita.com/harupython/items/3a52fb00f816c33598ff)をご覧ください。

## 機能

- IPアドレス収集（Bright Data経由のアクセスログから）
- proxycheck.io v3 APIによる検知テスト
- 並列処理による大量検証
- リアルタイム進捗表示（tqdm）
- 詳細な統計分析（検知率、リスクスコア、国別分布）
- CSV/JSON形式での結果エクスポート

## 必要要件

- Python 3.8以上
- Bright Dataアカウント（検証対象のIPアドレス収集用）
- proxycheck.io APIキー（推奨、無料プランは1,000リクエスト/日）
- tqdm（オプション、進捗表示用）

## インストール

```bash
git clone https://github.com/yourusername/brightdata-proxy-detection-test.git
cd brightdata-proxy-detection-test
pip install tqdm python-dotenv
```

## 使い方

### 1. 環境変数設定

`.env`ファイルを作成し、proxycheck.io APIキーを設定します。

```bash
PROXYCHECK_API_KEY=your_api_key_here
MAX_WORKERS=3
DELAY_BETWEEN_REQUESTS=1.0
```

### 2. IPアドレスを収集

Bright Data経由でアクセスを行い、IPLoggerなどでアクセスログを取得します。

```bash
# logger.pyでBright Data経由のアクセスを記録
python logger.py
```

### 3. 検証実行

収集したIPアドレスをproxycheck.io v3でチェックします。

```bash
# CSVからIPを抽出してチェック
python proxycheck.py IPLogger-output.csv results.json
```

### 4. 結果分析

```bash
# 統計分析とCSV出力
python analyze_results.py results.json
```

出力ファイル
- `proxycheck_stats.csv` - 全IP詳細データ
- `proxycheck_stats_summary.csv` - サマリー統計
- `proxycheck_stats_countries.csv` - 国別分布

## ファイル構成

```
├── logger.py              # Bright Data経由のアクセスログ収集
├── proxycheck.py          # proxycheck.io v3 APIでの検証
├── analyze_results.py     # 結果の統計分析
├── .env                   # 環境変数設定
└── README.md
```

## 検証結果サンプル

```
Total IPs: 475
Proxy detected: 2 (0.4%)
VPN detected: 0 (0.0%)
Average Risk Score: 0.42

Top 5 Countries:
  United States: 120 (25.3%)
  Brazil: 90 (18.9%)
  Mexico: 32 (6.7%)
  Vietnam: 31 (6.5%)
  Argentina: 23 (4.8%)
```

## API v3の変更点

proxycheck.io v2からv3への主な変更点

- エンドポイント: `v2` → `v3`
- レスポンス形式の改善
- より詳細な検知情報
- APIキー認証の強化

詳細は[公式ドキュメント](https://proxycheck.io/api/)を参照してください。

## 注意事項

⚠️ **免責事項**

このツールは教育・研究目的での使用を想定しています。

- proxycheck.ioの利用規約を遵守してください
- APIキーなしでの大量リクエストはレート制限されます
- 本ツールの使用により生じた損害について、作者は一切の責任を負いません

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照

## 参考

- [Qiita記事: 検証レポート](リンク)
- [Bright Data公式](https://brightdata.com/)
- [proxycheck.io API v3](https://proxycheck.io/api/)

## Author

[@harumaki4649](https://github.com/harumaki4649)
