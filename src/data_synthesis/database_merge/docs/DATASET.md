# CSpider 数据集详细说明

## 数据集概述

CSpider是一个中文文本到SQL的数据集，包含206个SQLite数据库和对应的自然语言查询对。每个数据库代表不同的应用场景，涵盖学术、商业、交通、教育等多个领域。

## 详细目录结构

```
CSpider/
├── char_emb.txt                    # 中文字符嵌入向量文件
├── database/                       # 训练数据库目录（158个）
│   ├── academic/                   # 学术数据库
│   │   ├── academic.sqlite         # SQLite数据库文件
│   │   └── schema.sql              # 数据库结构定义
│   ├── activity_1/                 # 活动数据库
│   ├── aircraft/                   # 飞机数据库
│   ├── allergy_1/                  # 过敏数据库
│   ├── apartment_rentals/          # 公寓租赁数据库
│   ├── ...                         # 其他数据库
│   └── wine_1/                     # 酒类数据库（包含CSV数据）
│       ├── wine_1.sqlite
│       ├── schema.sql
│       └── data_csv/               # CSV原始数据
│           ├── winemag-p1.csv
│           ├── winemag-p2.csv
│           └── ...
├── test_data/                      # 测试查询数据
└── test_database/                  # 测试数据库目录（48个）
    ├── aan_1/                      # 测试数据库
    │   ├── aan_1.sqlite
    │   └── schema.sql
    ├── address_1/                  # 地址数据库
    └── warehouse_1/                # 仓库数据库
```

## 数据库类型分类

### 1. 学术相关数据库
- **academic**: 学术论文和作者信息
- **scholar**: 学者研究领域
- **journal_committee**: 期刊委员会信息

### 2. 商业相关数据库
- **company_1**: 公司基本信息
- **company_employee**: 员工信息
- **customer_complaints**: 客户投诉记录
- **product_catalog**: 产品目录

### 3. 交通相关数据库
- **car_1**: 汽车制造商和型号信息
- **flight_1/flight_2**: 航班信息
- **aircraft**: 飞机信息
- **railway**: 铁路信息

### 4. 教育相关数据库
- **college_1/college_2/college_3**: 大学信息
- **student_1**: 学生信息
- **course_teach**: 课程教学信息

### 5. 娱乐相关数据库
- **cinema**: 电影院信息
- **music_1/music_2**: 音乐信息
- **movie_1**: 电影信息
- **concert**: 演唱会信息

### 6. 体育相关数据库
- **baseball_1**: 棒球信息
- **soccer_1/soccer_2**: 足球信息
- **basketball**: 篮球信息
- **wrestler**: 摔跤信息

### 7. 生活服务数据库
- **restaurant_1**: 餐厅信息
- **hospital_1**: 医院信息
- **inn_1**: 旅馆信息
- **department_store**: 百货商店

## 数据库文件格式

### SQLite数据库文件 (.sqlite)
- 每个数据库包含多个表
- 表结构在对应的schema.sql文件中定义
- 数据包含中文和英文内容

### Schema文件 (schema.sql)
- 定义数据库的表结构
- 包含CREATE TABLE语句
- 定义主键、外键约束
- 字段类型和约束条件

### CSV数据文件 (data_csv/)
- 7个数据库包含原始CSV数据
- 标准逗号分隔值格式
- 对应的README文件说明数据含义

### 自然语言查询文件
- **q.txt**: 自然语言查询的文本格式
- **annotation.json**: 结构化的查询标注
- 包含中文查询问题和对应的SQL查询

## 数据统计

### 数据库分布
- **总数量**: 206个数据库
- **训练集**: 158个数据库
- **测试集**: 48个数据库
- **包含CSV数据**: 7个数据库

### 数据库领域分布
- **学术**: ~20个
- **商业**: ~30个
- **交通**: ~25个
- **教育**: ~40个
- **娱乐**: ~30个
- **体育**: ~25个
- **生活服务**: ~36个

### 表数量统计
- **平均每数据库**: 5-15个表
- **最大表数量**: 25+个表
- **最小表数量**: 2-3个表
- **总计表数**: 预计1500+个表

## 字符嵌入文件 (char_emb.txt)

### 文件格式
```
字符 向量1 向量2 向量3 ... 向量N
涉 0.001269 -0.048217 -0.082927 ...
伊 0.062815 -0.103694 -0.093273 ...
随 -0.050390 0.338271 0.311132 ...
```

### 用途
- 为中文字符提供向量表示
- 支持中文文本的向量化处理
- 用于文本到SQL转换模型的嵌入层

## 查询标注格式

### 自然语言查询 (q.txt)
```
Find all Reanults ('renault') in the database. For each, report the name and the year.

Find all cars produced by Volvo between 1977 and 1981 (inclusive). Report the name of the car and the year it was produced.

Report all Asian automakers. Output the full name of the automaker and the country of origin
```

### 结构化标注 (annotation.json)
```json
{
    "label_id": null,
    "data": [
        {
            "nl": "Find all Reanults ('renault') in the database. For each, report the name and the year.",
            "id": 0
        },
        {
            "nl": "Find all cars produced by Volvo between 1977 and 1981 (inclusive). Report the name of the car and the year it was produced.",
            "id": 1
        }
    ]
}
```

## 使用示例

### 1. 查看数据库结构
```bash
# 查看特定数据库的表结构
cat CSpider/database/academic/schema.sql

# 使用SQLite客户端打开数据库
sqlite3 CSpider/database/academic/academic.sqlite

# 在SQLite中查看表
.tables
.schema
```

### 2. 查询数据
```sql
-- 查看作者信息
SELECT * FROM author LIMIT 10;

-- 查看论文信息
SELECT * FROM paper LIMIT 5;

-- 关联查询
SELECT a.name, p.title
FROM author a
JOIN paper p ON a.aid = p.aid;
```

### 3. 处理自然语言查询
```python
# 读取查询文件
with open('CSpider/database/academic/q.txt', 'r', encoding='utf-8') as f:
    queries = f.readlines()

# 读取标注文件
import json
with open('CSpider/database/academic/annotation.json', 'r', encoding='utf-8') as f:
    annotations = json.load(f)
```

## 注意事项

### 1. 编码问题
- 所有文件使用UTF-8编码
- 处理中文内容时需要注意编码转换
- 数据库中的中文字符需要正确的字符集支持

### 2. 数据质量
- 不同数据库的数据质量可能存在差异
- 部分数据库可能存在缺失值
- 建议在使用前进行数据清洗

### 3. 性能考虑
- 部分大型数据库加载时间较长
- 建议使用索引优化查询性能
- 可以考虑使用数据库连接池

### 4. 术语一致性
- 不同数据库可能使用不同的术语
- 字段命名可能存在不一致性
- 表结构设计风格可能有所差异

## 相关工具

- **analyze_sqlite_tables.py**: 分析所有数据库的表结构和统计信息
- **merge_sqlite_databases.py**: 将多个数据库合并为单一文件
- **SQLite Browser**: 图形化数据库查看工具
- **DBeaver**: 通用数据库管理工具

## 参考资料

- [CSpider原始项目](https://github.com/taolisi/CSpider)
- [SQLite官方文档](https://sqlite.org/docs.html)
- [中文文本到SQL转换相关研究](https://arxiv.org/search/?query=chinese+text+to+sql)