import json

if __name__ == '__main__':
    xxx = []

    with open("../使用向量模型为每个表找到相似的表/output/final/similarity_enhanced_tables.jsonl", encoding="utf-8") as f:

        for line in f:
            data = json.loads(line)

            xxx.append(data)

    print(len(xxx))

    yyy = json.load(open("sqlite_functions_groups.json", encoding="utf-8"))

    print(len(yyy))

    prompt_template = open("prompts/sqlite_schema_function_compatibility_prompt.txt", encoding="utf-8").read().strip()

    idx = 0

    ttt = []

    for data in xxx:
        table_name = data['table_name']
        create_sql = data['create_sql']
        sample_data = data['sample_data']
        annotated_ddl = data['annotated_ddl']
        table_summary = data['table_summary']
        similar_tables = data['similar_tables']

        MULTI_TABLE_SCHEMA_WITH_SAMPLES = []

        MULTI_TABLE_SCHEMA_WITH_SAMPLES.append({
            'table_name': table_name,
            'create_sql': annotated_ddl,
            'sample_data': sample_data,
        })

        for similar_table in similar_tables:
            table_name = similar_table['table_name']
            create_sql = similar_table['create_sql']
            sample_data = similar_table['sample_data']
            annotated_ddl = similar_table['annotated_ddl']
            table_summary = similar_table['table_summary']

            MULTI_TABLE_SCHEMA_WITH_SAMPLES.append({
                'table_name': table_name,
                'create_sql': annotated_ddl,
                'sample_data': sample_data,
            })

        for zzz in yyy:
            name = zzz['name']
            description = zzz['description']
            suitable_schemas = zzz['suitable_schemas']
            unsuitable_schemas = zzz['unsuitable_schemas']
            key_functions = zzz['key_functions']

            hhh = (prompt_template
             .replace("{FUNCTION_GROUP_NAME}", name)
             .replace("{FUNCTION_GROUP_DESCRIPTION}", description)
             .replace("{SUITABLE_SCHEMA_CHARACTERISTICS}", suitable_schemas)
             .replace("{UNSUITABLE_SCHEMA_CHARACTERISTICS}", unsuitable_schemas)
             .replace("{KEY_FUNCTIONS}", json.dumps(key_functions, ensure_ascii=False, indent=2))
             .replace("{MULTI_TABLE_SCHEMA_WITH_SAMPLES}", json.dumps(MULTI_TABLE_SCHEMA_WITH_SAMPLES, ensure_ascii=False, indent=2))
             )

            data['prompt_context'] = {}
            data['prompt_context']['template'] = prompt_template
            data['prompt_context']['filled'] = hhh

            data['idx'] = idx

            idx += 1

            ttt.append(data)

    with open("xxx.jsonl", "w", encoding="utf-8") as f:
        for data in ttt:
            f.write(json.dumps(data, ensure_ascii=False))
            f.write("\n")
            f.flush()
