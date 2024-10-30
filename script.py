import pandas as pd
import re
from textwrap import dedent
import util.ProjectSettings as ps
import util.GithubOperator as go
import hashlib
from datetime import datetime
import argparse

github_operator = go.GithubOperator()
myps = ps.ProjectSettings()


def clean_text(text: str) -> str:
    return dedent(text).strip()


def convert_body(row):
    additional_body = """
        ## PivotalTrackerより転載
        ### metadata
        - URL: {url}
        - Estimate: {estimate}
        - Type: {type}
        - Created At: {created_at}
        - Requested By: {requested_by}
        - Owned By: {owner}

        ### Pull Requests
        {pr_texts}
    """
    new_body = clean_text(row["body"]) + "\n" + clean_text(additional_body)
    return new_body.format(
        url=row["url"],
        estimate=row["estimate"],
        type=row["type"],
        created_at=row["created_at"],
        requested_by=row["requested_by"],
        owner=", ".join(row["owner"]),
        pr_texts="\n".join(row["pull_request"]),
    )


def add_comments(issue_id, comments):
    for comment in comments:
        base = """
        PivotalTrackerより転載

        {comment}
        """
        body = clean_text(base).format(comment=comment)
        github_operator.add_comment_to_issue(issue_id, body)


def update_field_value(project_item_id, target, project_setting, value):
    obj = None
    match target:
        case "story_type":
            obj = project_setting.story_type
        case "state":
            obj = project_setting.state
        case "estimate":
            obj = project_setting.estimate
    if obj is None or obj.github_field_id is None:
        # フィールドの設定がない場合は何もしない
        return

    github_operator.update_project_item_field_value(
        project_setting.github_project_id,
        project_item_id,
        obj.github_field_id,
        obj.github_field_type,
        obj.convert(value),
    )


def list_issues(owner, repository_name):
    repository_id, issues = github_operator.list_issues(owner, repository_name)
    new_issues = {}
    for issue in issues:
        new_issues[convert_hash(issue["title"])] = issue
    return repository_id, new_issues


def convert_issue_title(id, title):
    return f"[#{id}] {title}"


def convert_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


def remove_suffix_text(text):
    return re.sub(r"\.\d+$", "", text)


def merge_columns(row, column_name):
    # xxx.1, xxx.2, xxx.3, ... という列名がある場合、xxxの列に統合する。nullは無視する。
    columns = [column for column in row.index if column.startswith(column_name)]
    return [row[column] for column in columns if pd.notnull(row[column])]


def create_works_log_row(pivotal_obj, issue, result):
    return {
        "title": pivotal_obj["title"],
        "pivotal_url": pivotal_obj["url"],
        "github_url": issue["url"],
        "result": result,
    }


def read_file(file_path):
    df = pd.read_csv(file_path)
    pivotal_issues = []
    for i, row in df.iterrows():
        json = {
            "title": convert_issue_title(row["Id"], row["Title"]),
            "body": row["Description"],
            "type": row["Type"],
            "state": row["Current State"],
            "estimate": row["Estimate"],
            "requested_by": row["Requested By"],
            "owner": merge_columns(row, "Owned By"),
            "created_at": row["Created at"],
            "url": row["URL"],
            "pull_request": merge_columns(row, "Pull Request"),
            "git_branch": merge_columns(row, "Git Branch"),
            "comment": merge_columns(row, "Comment"),
        }
        pivotal_issues.append(json)
    return pivotal_issues


def create_or_find_for_github(repository_id, pivotal_issues, exists_issues):
    works = []
    for target_issue in pivotal_issues:
        project_id = myps.project.github_project_id
        title_hash = convert_hash(target_issue["title"])
        if title_hash in exists_issues:
            print(f'{target_issue["title"]} is already exists.')
            works.append(
                create_works_log_row(target_issue, exists_issues[title_hash], "exists")
            )
            continue

        new_issue = github_operator.create_issue(
            repository_id, target_issue["title"], convert_body(target_issue)
        )
        issue_id = new_issue["id"]
        add_comments(issue_id, target_issue["comment"])
        project_item_id = github_operator.add_issue_to_project(project_id, issue_id)
        # 各種フィールドの更新
        update_field_value(
            project_item_id, "story_type", myps.project, target_issue["type"]
        )
        update_field_value(
            project_item_id, "state", myps.project, target_issue["state"]
        )
        update_field_value(
            project_item_id, "estimate", myps.project, target_issue["estimate"]
        )

        print(f'{target_issue["title"]} is created.')
        works.append(create_works_log_row(target_issue, new_issue, "create"))
    return works


def main():
    parser = argparse.ArgumentParser(
        description="PivotalTrackerのStoryをGithubのIssue+Projectに変換して登録します"
    )
    # オプション引数の設定
    parser.add_argument(
        "-f", "--file", type=str, help="読み込むファイルパス", required=True
    )
    # 引数を解析
    args = parser.parse_args()

    # PivotalのCSVを読み込む
    pivotal_issues = read_file(args.file)
    print(f"Found {len(pivotal_issues)} issues.")
    # 既存のIssueを取得
    repository_id, exists_issues = list_issues(myps.owner, myps.repository_name)
    print(f"Found {len(exists_issues)} exist issues.")
    # Github連携処理
    works = create_or_find_for_github(repository_id, pivotal_issues, exists_issues)
    # 作業ログをCSVに出力
    df = pd.DataFrame(works)
    file_name = f"tmp/works_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    df.to_csv(file_name, index=False)
    print(f"Done. Works log is saved to {file_name}")


if __name__ == "__main__":
    main()
