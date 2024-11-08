import pandas as pd
import numpy as np
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
    if text is None or text == "" or pd.isnull(text):
        return ""
    return dedent(text).strip()


def convert_body(row, columns):
    additional_body_base = """
        ## PivotalTrackerより転載
        {additional_fields}
        ### Pull Requests
        {pr_texts}
    """
    additional_fields = ""
    for column_name, column in columns.items():
        if column.include_description():
            additional_fields += f"- {column_name}: {row[column_name]}\n"

    additional_body = clean_text(additional_body_base).format(
        additional_fields=additional_fields.strip(),
        pr_texts="\n".join(merge_columns(row, "Pull Request")),
    )
    return clean_text(row["Description"]) + "\n" + additional_body


def add_comments(issue_id, comments):
    for comment in comments:
        base = """
        PivotalTrackerより転載

        {comment}
        """
        body = clean_text(base).format(comment=comment)
        github_operator.add_comment_to_issue(issue_id, body)


def update_field_value(project_id, project_item_id, filed_value, value):
    if filed_value is None or filed_value.github_field_id is None:
        # フィールドの設定がない場合は何もしない
        return

    github_operator.update_project_item_field_value(
        project_id,
        project_item_id,
        filed_value.github_field_id,
        filed_value.github_field_type,
        filed_value.convert(value),
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
    columns = [column for column in list(row.keys()) if column.startswith(column_name)]
    return [row[column] for column in columns if pd.notnull(row[column])]


def create_works_log_row(pivotal_obj, issue, result):
    return {
        "title": convert_issue_title(pivotal_obj["Id"], pivotal_obj["Title"]),
        "pivotal_url": pivotal_obj["URL"],
        "github_url": issue["url"],
        "result": result,
    }


def read_file(file_path):
    df = pd.read_csv(file_path)
    df = df.replace([np.nan], [None])
    return df.to_dict(orient="records")


def update_field_values(project_id, project_item_id, pivotal, columns):
    for column_name, column in columns.items():
        if column.exist_field_value():
            update_field_value(
                project_id, project_item_id, column.field_value, pivotal[column_name]
            )
    return pivotal


def create_or_find_for_github(repository_id, pivotal_issues, exists_issues):
    works = []
    for pivotal in pivotal_issues:
        project_id = myps.project.github_project_id
        issue_title = convert_issue_title(pivotal["Id"], pivotal["Title"])
        title_hash = convert_hash(issue_title)
        if title_hash in exists_issues:
            print(f"{issue_title} is already exists.")
            works.append(
                create_works_log_row(pivotal, exists_issues[title_hash], "exists")
            )
            continue

        print(f"{issue_title} is creating....")
        issue_body = convert_body(pivotal, myps.project.columns)
        new_issue = github_operator.create_issue(repository_id, issue_title, issue_body)
        issue_id = new_issue["id"]
        add_comments(issue_id, merge_columns(pivotal, "Comment"))
        project_item_id = github_operator.add_issue_to_project(project_id, issue_id)
        # 各種フィールドの更新
        update_field_values(project_id, project_item_id, pivotal, myps.project.columns)
        print(f"{issue_title} is created.")
        works.append(create_works_log_row(pivotal, new_issue, "create"))
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
