# SSStudio — App Store Screenshot Composer

macOSローカル環境で動作する、App Store Connect掲載用スクリーンショット画像を高速・高品質に作成・量産するためのGUIデスクトップアプリケーションです。

---

## 🌟 主な特徴

1. **App Store プリセット対応**
   - iPhone 6.9-inch (1290 × 2796)
   - iPhone 6.5-inch (1242 × 2688)
   - iPhone 6.3-inch (1206 × 2622)
   - iPad 13-inch (2064 × 2752)
   - カスタム解像度入力対応

2. **高級黒背景グラデーション（Luxury Black Preset）**
   - 落ち着いた深みのある黒グラデーション（縦・横・斜め）
   - 微妙な光沢感を演出する**ラジアル・スポットライト（Spotlight）**機能
   - 8-bitバンディング（色の階調割れ）を防ぐ高品質ディザリング生成
   - プリセット: Luxury Black / Charcoal Black / Soft Spotlight Black / Pure Black / Pure White / Soft Studio Gray

3. **端末風フレーム（角丸＋ボーダー＋リアルソフトシャドウ）**
   - 公式フレーム素材不要で高品質な端末風演出
   - Corner Radius（角丸）
   - Border Width / Border Color
   - Gaussian BlurによるなめらかなDrop Shadow（Opacity / Blur / Offset）

4. **高速量産テンプレート & テーマ機能**
   - **Headline Top**: 上部に大見出し＋サブコピー、中央〜下部に端末画像
   - **Split**: 左（上）にコピー、右（下）に端末画像
   - **Center Device**: 中央に大きく端末画像、上下に見出しとキャプション
   - **Double Device**: 2枚の端末画像を少し重ねて配置（角度調整可能）
   - **Free Layout**: 完全自由配置
   - **Lememo Luxury Theme**: 高級感のあるダークトーン、アクセントカラー（`#B34254`）の即時適用

5. **マルチページ & 一括連番PNG書き出し（Export All）**
   - 1つのプロジェクト内で複数ページ（Page 1, Page 2...）を管理
   - **ページ複製（Duplicate Page）**: 背景・フォントスタイル・端末レイアウトを保ったまま、スクリーンショットとテキストだけを素早く差し替え
   - **Export All**: `01_people.png`, `02_memory.png`, `03_schedule.png` のように指定サイズ・RGB PNGで一括書き出し

6. **日本語フォント & タイポグラフィ**
   - macOS標準フォント（ヒラギノ角ゴシック W3/W6/W8、Helvetica Neue、Avenir Next等）
   - Hero / Headline / Subheadline / Caption プリセット
   - 自動折り返し（Max Width）、行間・文字揃え（左/中央/右）、太字（Bold）

7. **プロジェクト保存 / 復元**
   - JSON形式で全ページ・全レイヤー・スタイル・位置を保存・再読み込み可能

---

## 🛠️ 動作要件

- OS: macOS (Apple Silicon / Intel)
- Python 3.10 以上（Tkinter有効）
- ライブラリ: Pillow, numpy

---

## 🚀 セットアップ & 起動方法

### 1. リポジトリの確認
```bash
cd /Users/motonari/Antigravity/SSStudio
```

### 2. 仮想環境 (venv) の作成と有効化
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 4. アプリケーションの起動
```bash
python app.py
```

> **※Homebrew Pythonを使用している場合の注意**:
> HomebrewのPython 3.14環境でTkinterが必要な場合は `brew install python-tk@3.14` を実行してください。

---

## 📖 操作ガイド

### 画面構成（3カラムレイアウト）
- **左側パネル（Canvas & Background）**:
  - **Canvas Preset & Size**: 端末プリセット選択（iPhone 6.9/6.5/6.3, iPad 13, Custom）、カスタムサイズ変更
  - **Background & Gradient**: 高級黒グラデーション、開始/終了色、方向、ラジアルスポットライトの調整
- **中央エリア（Page Bar & Preview Canvas）**:
  - **上部ページバー**: `+ Add Page`, `⧉ Duplicate Page`, `✏ Rename`, `✕ Delete`, ページ切り替え
  - **プレビューキャンバス**: 実寸比率プレビュー、マウスドラッグ移動、四隅ハンドルによる拡大縮小
- **右側パネル（Layers & Layer Properties）**:
  - **Layers**: レイヤー一覧、重なり順の変更（▲/▼）、レイヤー複製・削除、新規スクリーンショット/テキスト追加
  - **Layer Properties**: 選択中レイヤーの細かなパラメータ調整（角丸、影、枠線、フォント、文字色、行間、最大幅など）に特化し、縦に見切れることなくゆったりと編集可能
- **上部ツールバー**:
  - `New` / `Open` / `Save`: プロジェクト管理（JSON）
  - `Template`: 選択したテンプレートを現在のページに適用
  - `✨ Lememo Luxury Theme`: Le'memo向けラグジュアリー黒テーマを一発適用
  - `📐 Guides`: セーフマージン（5%/10%）や見出しエリアのガイド表示切替（エクスポート画像には含まれません）
  - `Export PNG`: 現在のページを実寸PNG出力
  - `⚡ Export All PNGs`: 全ページを連番PNGとして一括書き出し

---

## 画像の非破壊Crop

画像レイヤーを選択し、Layer Properties の **Crop...** で編集します。
枠内のドラッグで移動、四隅・辺のドラッグでサイズ変更できます。
**Apply** で確定し、**Cancel** またはウィンドウを閉じると変更を破棄します。
ダイアログの **Reset** は編集範囲を全体に戻し、Applyで確定します。
パネルの **Reset Crop** は即座に全体へ戻します。**Replace Image...** でもCropはリセットされます。

Cropは元画像を書き換えず、正規化座標としてProject JSONに保存します。
Crop項目のない旧JSONは画像全体として読み込めます。
最小範囲は各辺が元画像の1%以上（最低1ピクセル）。M1はFree Cropのみ対応します。
画像の表示幅は従来どおりScaleで決まり、高さはCrop後の縦横比に従います。

---

## 📁 ディレクトリ構成

```text
SSStudio/
├── app.py                     # エントリーポイント
├── requirements.txt           # 依存パッケージ定義
├── README.md                  # 取扱説明書
├── core/
│   ├── models.py              # データモデル (Project, Page, ImageLayer, TextLayer, FrameConfig, GradientConfig)
│   ├── fonts.py               # macOS日本語・欧文フォントローダー
│   ├── renderer.py            # PIL/numpyによる高解像度レンダリングエンジン
│   ├── templates.py           # App Store量産用テンプレート & テーマ定義
│   ├── exporter.py            # 単一/一括RGB PNGエクスポーター
│   └── project.py             # JSONプロジェクト保存・読み込み
├── ui/
│   ├── theme.py               # macOSダークスタイルUI定数
│   ├── canvas_view.py         # ドラッグ&リサイズ対応プレビューキャンバス
│   ├── page_manager.py        # 複数ページタブ管理バー
│   ├── property_panel.py      # インスペクター & レイヤー管理パネル
│   └── main_window.py         # メインウィンドウ
├── demo_assets/               # デモ用サンプルスクリーンショット
└── tests/                     # ユニット・統合テスト
```

---

## 🧪 テストの実行

```bash
./venv/bin/python -m unittest discover tests
```
