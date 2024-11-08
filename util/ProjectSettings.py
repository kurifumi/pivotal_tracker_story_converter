import json


class FieldValue:
    def __init__(self, json):
        self.github_field_id = json["github_field_id"]
        self.github_field_type = json["github_field_type"]
        self.mappings = json.get("mappings", {})

    def convert(self, pivotal_key):
        if self.github_field_type != "SINGLE_SELECT":
            return pivotal_key
        return self.mappings.get(pivotal_key, None)


class Column:
    def __init__(self, json):
        self.write_description = (
            json["write_description"] if "write_description" in json else False
        )
        self.field_value = (
            FieldValue(json["field_value"]) if "field_value" in json else None
        )

    def include_description(self):
        return self.write_description

    def exist_field_value(self):
        return self.field_value is not None


class Project:
    def __init__(self, json):
        self.github_project_id = json["github_project_id"]
        self.columns = {
            column_name: Column(column)
            for column_name, column in json["columns"].items()
        }


class ProjectSettings:
    _data = None

    def __init__(self):
        # Load data from file if not already loaded
        if ProjectSettings._data is None:
            with open("project.json") as f:
                ProjectSettings._data = json.load(f)

        self.owner = ProjectSettings._data["owner"]
        self.repository_name = ProjectSettings._data["repository_name"]
        self.project = Project(ProjectSettings._data["project"])
