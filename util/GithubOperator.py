import requests
import time
import os


class GithubSubmitTooQuicklyException(Exception):
    def __init__(self, message="You are submitting too quickly to GitHub."):
        super().__init__(message)
        return None


class GithubOperator:
    COMMON_REQUEST_INTERVAL = 1
    CREATE_REQUEST_INTERVAL = 24

    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        self.endpoint = "https://api.github.com/graphql"
        self.auth_headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        }
        self.last_request_time = None
        self.last_create_request_time = None

    def create_issue(self, repository_id, title, body):
        query = """
            mutation CreateIssue($input: CreateIssueInput!) {
                createIssue(input: $input) {
                    issue {
                        id
                        title
                        number
                        url
                    }
                }
            }
        """
        variables = {
            "input": {"repositoryId": repository_id, "title": title, "body": body}
        }
        response = self._request(query, variables, True)
        response.raise_for_status()  # エラー処理
        return response.json()["data"]["createIssue"]["issue"]

    def add_comment_to_issue(self, issue_id, body):
        query = """
            mutation AddComment($issueId: ID!, $body: String!) {
                addComment(input: {subjectId: $issueId, body: $body}) {
                    commentEdge {
                        node {
                            id
                            body
                        }
                    }
                }
            }"""
        variables = {
            "issueId": issue_id,
            "body": body,
        }
        response = self._request(query, variables)
        body = response.json()
        response.raise_for_status()  # エラー処理

    def add_issue_to_project(self, project_id, issue_id):
        query = """
            mutation ($input: AddProjectV2ItemByIdInput!){
                addProjectV2ItemById(input: $input) {
                    item {
                        id
                    }
                }
            }
        """
        variables = {"input": {"projectId": project_id, "contentId": issue_id}}
        response = self._request(query, variables)

        response.raise_for_status()  # エラー処理
        return response.json()["data"]["addProjectV2ItemById"]["item"]["id"]

    def list_issues(self, owner, name):
        query = """
            query ($after: String!, $owner: String!, $name: String!) {
                repository(owner: $owner, name: $name) {
                    id
                    issues(first: 100, after: $after) {
                        totalCount
                        edges {
                            node {
                                id
                                title
                                number
                                url
                            }
                        }
                        pageInfo {
                            endCursor
                            hasNextPage
                        }
                    }
                }
            }
        """
        variables = {"after": "", "owner": owner, "name": name}
        repository_id = None
        issues = []
        while True:
            response = self._request(query, variables)
            data = response.json()["data"]
            repository = data["repository"]
            repository_id = repository["id"]
            for issue in repository["issues"]["edges"]:
                issues.append(issue["node"])
            if not repository["issues"]["pageInfo"]["hasNextPage"]:
                break
            variables["after"] = repository["issues"]["pageInfo"]["endCursor"]
        return repository_id, issues

    def update_project_item_field_value(
        self, project_id, project_item_id, field_id, field_data_type, option_value
    ):
        query = """
            mutation ($input: UpdateProjectV2ItemFieldValueInput!){
                updateProjectV2ItemFieldValue(input: $input) {
                    projectV2Item {
                        id
                    }
                }
            }
        """
        if (
            field_data_type == "NUMBER"
            and option_value != ""
            and option_value is not None
        ):
            # 数値型の場合はoption_valueを数値に変換
            option_value = int(option_value)

        variables = {
            "input": {
                "projectId": project_id,
                "itemId": project_item_id,
                "fieldId": field_id,
                "value": {self._option_value_key(field_data_type): option_value},
            }
        }
        response = self._request(query, variables)

        response.raise_for_status()  # エラー処理
        project_item_id = response.json()["data"]["updateProjectV2ItemFieldValue"][
            "projectV2Item"
        ]["id"]

    def _request(self, query, variables, is_create_query=False, retry_count=0):
        self._wait_request(is_create_query)
        request_time = time.time()
        response = requests.post(
            self.endpoint,
            headers=self.auth_headers,
            json={"query": query, "variables": variables},
        )
        # リクエスト時間の記録
        self.last_request_time = request_time
        if is_create_query:
            self.last_create_request_time = request_time
        try:
            self._handle(response)
        except GithubSubmitTooQuicklyException:
            if retry_count > 15:
                raise Exception("TooQuicklyが解消されないため、処理を中断します")
            print("TooQuicklyExceptionが発生した為、1分待機")
            time.sleep(60)  # 1分待つ
            retry_count += 1
            return self._request(query, variables, is_create_query, False)
        return response

    def _wait_request(self, is_create_query):
        if is_create_query and self.last_create_request_time is not None:
            # 24秒待つとリクエストが安定するらしい
            # https://github.com/cli/cli/issues/4801
            self.wait_for(self.last_create_request_time, 24)
        if self.last_request_time is not None:
            self.wait_for(self.last_request_time)

    def wait_for(self, last_request_time, interval_sec=1):
        while True:
            elapsed_time = time.time() - last_request_time
            if elapsed_time >= interval_sec:
                break
            time.sleep(max(0, interval_sec - elapsed_time))

    def _handle(self, response):
        response.raise_for_status()
        if "errors" in response.json():
            error = response.json()["errors"][0]
            # issueなど特定のリソースは実行間隔が厳しく、抵触すると下記のエラーが出る
            # https://github.com/cli/cli/issues/4801
            if error["message"] == "was submitted too quickly":
                raise GithubSubmitTooQuicklyException()
            raise Exception(response.json()["errors"])

    def _option_value_key(self, data_type):
        match data_type:
            case "NUMBER":
                return "number"
            case "ITERATION":
                return "iterationId"
            case "SINGLE_SELECT":
                return "singleSelectOptionId"
            case "TEXT":
                return "text"
            case "DATE":
                return "date"
        return None
