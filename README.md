# PivotalTrackerStoryConverter

PivotalTracker の Story から GithubIssue ならびに Project に変換します。

## 事前準備

### Github (WebUI)

- GithubProject を生成
- 作成した GithubProject の Field に下記 3 つを追加（名称は任意）
  - Type (SingleSelect)
  - Estimate (Number)
  - State (SingleSelect)

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

```
python3 script.py -f {ファイル名}
```

## マッピング

| Pivotal        | Github                               |
| -------------- | ------------------------------------ |
| Id             | Issue.title (※接頭辞に付与)          |
| Title          | Issue.title                          |
| Label          | 移行対象外                           |
| Iteration      | 移行対象外                           |
| IterationStart | 移行対象外                           |
| IterationEnd   | 移行対象外                           |
| Type           | Project の FieldValue として移行可能 |
| Estimate       | Project の FieldValue として移行可能 |
| Priority       | 移行対象外                           |
| CurrentState   | Project の FieldValue として移行可能 |
| CreatedAt      | Issue: body に追記                   |
| AcceptedAt     | 移行対象外                           |
| Deadline       | 移行対象外                           |
| RequestedBy    | Issue.body に追記                    |
| Description    | Issue.body                           |
| URL            | Issue.body に追記                    |
| OwnedBy        | Issue.body に追記                    |
| Comment        | IssueComment                         |
| PullRequest    | Issue.body に追記                    |
| GitBranch      | 移行対象外                           |
