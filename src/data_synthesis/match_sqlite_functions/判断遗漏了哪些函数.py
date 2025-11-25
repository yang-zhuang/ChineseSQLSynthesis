import json


data = json.load(open("sqlite_functions_groups.json", encoding="utf-8"))

all_key_functions = []

for item in data:

    key_functions = item['key_functions']

    all_key_functions.extend(key_functions)

所有函数名称和描述 = []
with open("sqlite_functions_zh_description.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)

        所有函数名称和描述.extend(list(data.keys()))

for key_functions in all_key_functions:
    if key_functions not in 所有函数名称和描述:
        print(key_functions)