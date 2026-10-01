# SSStudio — App Store / Google Play Screenshot Composer

macOSローカル環境で動作する、Apple App Store / Google Play掲載用スクリーンショット画像を高速・高品質に作成・量産するためのGUIデスクトップアプリケーションです。

---

## 🌟 主な特徴

1. **Apple App Store / Google Play プリセット対応**
   - iPhone 6.9-inch (1290 × 2796)
   - iPhone 6.5-inch (1242 × 2688)
   - iPhone 6.3-inch (1206 × 2622)
   - iPad 13-inch (2064 × 2752)
   - Google Play Phone / Tablet: Portrait (1080 × 1920)、Landscape (1920 × 1080)
   - Storeを保持するカスタム解像度入力対応

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
cd ssstudio
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
  - **Canvas Preset & Size**: Store選択（Apple App Store / Google Play）、端末プリセット選択、カスタムサイズ変更
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

## Google Play / Android スクリーンショット

左パネルの **Store** で **Google Play** を選び、**Preset** を選択します。

| Preset | サイズ | device_type | orientation |
| --- | --- | --- | --- |
| Phone Portrait | 1080 × 1920 | phone | portrait |
| Phone Landscape | 1920 × 1080 | phone | landscape |
| Tablet Portrait | 1080 × 1920 | tablet | portrait |
| Tablet Landscape | 1920 × 1080 | tablet | landscape |

PhoneとTabletは同じ解像度でも別Profileとして扱います。
Profileは `name`、`store`、`device_type`、`orientation`、`width`、`height`、`description` を持ちます。
Project JSONには従来の `preset_name`・寸法に加えてStore・端末種別・向きを保存します。
向きは実際の寸法から求め、正方形は `square` とします。
Store情報のない旧Projectも読み込め、既存Appleの寸法やM1 Cropは維持されます。

**Size → Apply** でCustomに切り替えると、現在のStoreと端末種別を保持します。
CustomのままStoreを切り替えた場合は寸法を保持します。
既存と同様、Preset一覧から **Custom** を選択した場合の初期寸法は1290 × 2796です。
Google Playで使用する場合は、次の条件を満たす寸法に変更してください。

**Export PNG / Export All PNGs** は、Google Play（Customを含む）に対して以下を検証します。

- 幅・高さがそれぞれ **320〜3840 px**（境界値を含む）
- **長辺 ≤ 短辺 × 2**（ちょうど2:1は有効）

不適合の場合は理由を表示し、ファイルを書き出さずに停止します。
出力は従来どおりRGB PNGです。Apple向けExportへの新しい寸法制限はありません。
M2はPhone / Tabletの基本スクリーンショット対応で、7-inch / 10-inch専用フローやFeature Graphic生成は含みません。

---

## 画像の非破壊Crop

画像レイヤーを選択し、Layer Properties の **Crop...** で編集します。
枠内のドラッグで移動、四隅・辺のドラッグでサイズ変更できます。
**Apply** で確定し、**Cancel** またはウィンドウを閉じると変更を破棄します。
ダイアログの **Reset** は編集範囲を全体に戻し、Applyで確定します。
パネルの **Reset Crop** は即座に全体へ戻します。**Replace Image...** でもCropはリセットされます。

Cropは元画像を書き換えず、正規化座標としてProject JSONに保存します。
Crop項目のない旧JSONは画像全体として読み込めます。
**Aspect** で **Free / Original / 1:1 / 9:16 / 16:9** を選べます。
Originalは読み込んだ元画像の縦横比を使います。比率を変更すると現在の選択範囲内に収まる最大の枠へ調整し、
中心を可能な限り維持します。最小サイズの確保が必要な場合だけ枠を広げ、画像内に収めます。
固定比率では四隅・辺のドラッグでも比率を保ち、画像の外へはみ出しません。
**Reset** はFreeに戻して画像全体を選択します（Applyで確定）。
比率モード自体は保存せず、再度開いたCrop EditorはFreeになります。

最小範囲は各辺が元画像の1%以上（最低1ピクセル）。Apply時にピクセル境界へ丸めるため、
実際のCrop寸法は理想的な比率から最大1ピクセル程度ずれることがあります。
極端に細い画像など、比率・画像境界・最小サイズを同時に満たせない場合は理由を表示し、選択を維持します。
画像の表示幅は従来どおりScaleで決まり、高さはCrop後の縦横比に従います。

---

## Panorama / Multi-Screen Workspace

Canvas設定の **Workspace** で **Panorama** を選び、**Screens: 2 / 3 / 4** を指定します。
横方向の連続キャンバスとして、画像・Crop済み画像・テキストを画面境界をまたいで配置できます。
背景Gradient・SpotlightもWorkspace全体に一度だけ描画されます。
**Guides** をONにすると境界線と画面番号が表示されます。これらは出力には含まれません。

- 1 Page = 1 Workspace。既存のページタブ・複製・名前変更・削除はそのまま利用できます。
- Panorama設定はPageごとに保存されるため、3画面のPageと2画面のPageを混在できます。
- Canvas寸法は1画面分。1080 × 1920・3画面ならWorkspaceは3240 × 1920です。
- Singleとの切替やProfile変更でレイヤー座標を移動・削除・比例拡縮しません。
  Singleへ戻すと2画面目以降のレイヤーは画面外になりますが、データは保持されます。
- 画像Scaleとテキストの自動幅の基準は従来の1画面幅を維持します。
  横長の見出しは **Max W** を広げて配置できます。
- PreviewはWorkspace全体をfit表示し、Panoramaでは表示解像度で描画します。
  最終Exportは実寸で描画します。

**Export PNG** で選択するファイル名はPanoramaのベース名になります。
`feature.png` を指定した3画面のPageは `feature_01.png`〜`feature_03.png` を生成します。
**Export All PNGs** はページ順・画面順に、例えば以下を生成します。

```text
01_people_01.png
01_people_02.png
01_people_03.png
02_memory_01.png
02_memory_02.png
```

各PNGはCanvas設定と同じ寸法のRGB画像です。
Workspaceを一度描画してから整数座標でsliceするため、画面境界にgapやoverlapは発生しません。
Google Playの寸法検証は各sliceの寸法へ適用します。
既存の出力ファイルがある場合は書き込み前に上書きを確認します。
Single Pageは従来どおり1つのPNGを出力します。

保存形式はPage内の `panorama: {enabled, screen_count, direction}` を追加しています。
画面幅・高さはProjectの `canvas_width` / `canvas_height` を共通の情報源とし、
Profile変更時にWorkspace寸法が自動更新されます。Panorama情報のない旧JSONはSingleとして読み込みます。
M3は横方向の2〜4画面のみ対応し、縦方向や画面ごとの独立サイズ・背景は対象外です。

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

## Image Effects (M1.2)

画像レイヤーの **Image Effects** で次の効果を設定できます。

- **Bottom Fade**: Start / End（0〜1）で指定した画像下部を徐々に透明化します。元PNGのalphaにフェードを掛け合わせます。
- **Drop Shadow**: 画像のalpha形状に沿った影。Opacity、Blur、Offset X / Y、Colorを設定できます。Device Frame & Shadowの影とは独立して併用できます。
- **Reset Effects**: 両効果をOFFにし、初期設定に戻します。新規画像・旧プロジェクトでは両効果ともOFFです。

効果は非破壊のプロジェクト設定として保存され、元画像ファイルは変更しません。Free Crop / Crop Ratio Presetsと併用でき、切り抜き・リサイズ後の画像に適用します。画像とImage Shadowは同じグループで透明度・回転を適用します。Frameのボーダーはフェード対象外です。既存Frame Shadowの描画挙動は維持します。

Panoramaはワークスペース全体を描画してから分割するため、画面境界でもフェードと影が連続します。Previewは縮小したblur・offsetで描画し、Export Current / Export Allは高解像度のRGB PNGを出力します。M1.2のフェード方向はBottomのみです。

## Inspector操作 (M1.3)

右側のプロパティはスクロールバー、マウスホイール、macOSトラックパッドで縦スクロールできます。小さいウィンドウでも下部の項目へ移動できます。Slider上のホイールはパネルをスクロールし、Sliderの値を変更しません。Sliderをドラッグ中はホイールによるパネル移動を抑制します。

画像のTransform / Crop / Image Effects / Device Frame & Shadow、テキストのTransform / Text / Typographyは見出しクリックで折りたためます。開閉状態はレイヤー種類・セクションごとにアプリ起動中のみ保持します。左側のCanvas設定も同じ方法でスクロールできます。
