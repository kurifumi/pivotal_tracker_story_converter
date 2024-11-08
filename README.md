# PivotalTrackerStoryConverter

PivotalTracker の Story から GithubIssue ならびに Project に変換します。

## 事前準備

### Github (WebUI)

- GithubProject を生成
- [Personal access tokens](https://github.com/settings/tokens) ページから Token を入手
  - 必要な権限： repo(読み込み・書き込み)、project(読み込み・書き込み)
  - 入手したトークンは環境変数 `GITHUB_TOKEN` に設定してください

### Github (ソースコード)

- ライブラリインストール

```sh
# 必要に応じて仮想環境を作成、立ち上げてください
python3 -m venv venv
source venv/bin/activate

# ライブラリインストール
pip3 install -r requirements.txt
```

- `project.sample.json` を `project.json` としてコピー
- 必要な値を実際の ID に書き換える

### PivotalTracker

- CSV 出力し、スクリプトが参照できる場所に配置

## 使い方

```sh
export GITHUB_TOKEN=ghp_xxxxxxxxxxx
python3 script.py -f {ファイル名}

# または

GITHUB_TOKEN=ghp_xxxxxxxxxxx python3 script.py -f {ファイル名}
```

## 注意点

- RateLimit に抵触することを避ける為、Github へのリクエストは間隔を開けるように制御しています
  - Issue 作成リクエスト：最後に Issue を作成してから 24 秒
  - 全リクエスト：1 秒

## マッピング

Pivotal から出力された CSV カラムのマッピングは下記の通りです。

### 自動移行項目

- 下記項目は自動的に移行されます

| Pivotal      | Github                      |
| ------------ | --------------------------- |
| Id           | Issue.title (※接頭辞に付与) |
| Title        | Issue.title                 |
| Description  | Issue.body                  |
| Comment      | IssueComment                |
| Pull Request | Issue.body (※末尾に追記)    |

### 任意移行項目

- その他項目については `project.json` に設定を定義することで情報を移行することが可能です。
- Issue.body に追記する以外に、Project の FiledValue に値を紐づけることも可能です。

```json
{
  "project": {
    "columns": {
      "${PivotalColumnName}": {
        "write_description": true,
        "field_value": {
          "github_field_id": "PVTSSF_xxxxxxxx",
          "github_field_type": "SINGLE_SELECT",
          "mappings": {
            "feature": "aaaaaaaa",
            "bug": "bbbbbbbb",
            "chore": "cccccccc",
            "release": "dddddddd"
          }
        }
      }
    }
  }
}
```

| key                         | Github                                                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ${PivotalColumnName}        | Pivotal のカラム名（※半角スペースはそのまま）                                                                                                                 |
| write_description           | True の場合は Description に追記します（default: false）                                                                                                      |
| field_value                 | GithubProject の FiledValue に移行する場合に使用します。使用しない場合は省略可。                                                                              |
| filed_value.github_filed_id | Github の `filed.id` または `singleSelectFiled.id`                                                                                                            |
| filed_value.filed_type      | フィールド型（ `NUMBER` , `TEXT` , `SINGLE_SELECT`）                                                                                                          |
| filed_value.mappings        | `filed_value.filed_type = "SINGLE_SELECT"` のみ使用。値に対するプルダウンの値と Github の `singleSelectField.option.id` を key-value の形でマッピングします。 |

### 各種 ID の調べ方

[Github GraphQL Explorer](https://docs.github.com/ja/graphql/overview/explorer) から調べる方法がおすすめです。

### project.id

```graphQL
query {
  organization(login: "your_organization_name") {
    projectsV2(first: 100) {
      nodes {
        id
        title
        number
        createdAt
      }
    }
  }
}
```

### field.id, singleSelectField, singleSelectField.option.id

```graphQL
query {
  node(id: "your_github_project_id") {
    ... on ProjectV2 {
        field (name: "your_filed_value_name") {
            ... on ProjectV2SingleSelectField {
                id
                name
                dataType
                options {
                    id
                    name
                }
            },
            ... on ProjectV2Field {
                id
                name
                dataType
            }
        }
    }
  }
}

```
