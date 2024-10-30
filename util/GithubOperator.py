import requests


class GithubOperator:
    def __init__(self):
        token = "ghp_XXXXXXXX"
        self.endpoint = "https://api.github.com/graphql"
        self.auth_headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        }

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
        response = requests.post(
            self.endpoint,
            headers=self.auth_headers,
            json={"query": query, "variables": variables},
        )
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
        response = requests.post(
            self.endpoint,
            headers=self.auth_headers,
            json={"query": query, "variables": variables},
        )
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
        response = requests.post(
            self.endpoint,
            headers=self.auth_headers,
            json={"query": query, "variables": variables},
        )

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
            response = requests.post(
                self.endpoint,
                headers=self.auth_headers,
                json={"query": query, "variables": variables},
            )
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
        if field_data_type == "NUMBER" and option_value != "":
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
        response = requests.post(
            self.endpoint,
            headers=self.auth_headers,
            json={"query": query, "variables": variables},
        )

        response.raise_for_status()  # エラー処理
        project_item_id = response.json()["data"]["updateProjectV2ItemFieldValue"][
            "projectV2Item"
        ]["id"]

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
