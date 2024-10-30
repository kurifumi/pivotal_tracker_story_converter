import json


class ProjectSettings:
    class Project:
        class FieldValue:
            def __init__(self, json):
                self.github_field_id = json['githubFieldId']
                self.github_field_type = json['githubFieldType']
                self.mappings = json['mappings'] if 'mappings' in json.keys() else {}

            def convert(self, pivotal_key):
                if self.github_field_type != 'SINGLE_SELECT':
                    return pivotal_key
                if pivotal_key in self.mappings.keys():
                    return self.mappings[pivotal_key]
                return None

        def __init__(self, json):
            self.github_project_id = json['githubProjectId']
            self.state = self.FieldValue(json['state'])
            self.story_type = self.FieldValue(json['storyType'])
            self.estimate = self.FieldValue(json['estimate'])

    _data = None

    def __init__(self):
        # 情報がまだロードされていない場合のみ、ファイルから読み込む
        if ProjectSettings._data is None:
            with open('project.json') as f:
                ProjectSettings._data = json.load(f)

        self.owner = ProjectSettings._data['owner']
        self.repository_name = ProjectSettings._data['repository_name']
        self.project = self.Project(ProjectSettings._data['project'])
