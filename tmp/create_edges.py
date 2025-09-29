import pandas as pd

# --- 配置 ---
# 输入文件
name_csv = 'codeforces_problems_with_solved.csv'  # 原始数据，需要其中的 tags 列
problems_csv = 'problems.csv'  # 上一步生成的，需要其中的 id 和 title
result_csv = 'result.csv'  # 第一步生成的，知识点 ID 和名称的映射

# 输出文件
output_filename = 'edges.csv'

try:
    # 1. 读取需要用到的文件
    df_name = pd.read_csv(name_csv)
    df_problems = pd.read_csv(problems_csv)
    df_result = pd.read_csv(result_csv)
    print("成功读取 name.csv, problems.csv, 和 result.csv 文件。")

    # 2. 准备数据
    # 2.1 筛选 name.csv，保持与 problems.csv 的行对应
    #   与上一步完全相同的逻辑：丢弃 rating 为空的行
    df_name_filtered = df_name.dropna(subset=['rating']).copy()

    #   重置索引，确保可以和 df_problems 的行完美对齐
    df_name_filtered.reset_index(drop=True, inplace=True)
    df_problems.reset_index(drop=True, inplace=True)

    # 2.2 将 problem_id (P1, P2...) 添加到原始数据中，建立初始关联
    #   因为 df_problems 就是从 df_name_filtered 生成的，所以它们的行是一一对应的
    df_name_filtered['subject_id'] = df_problems['id']

    # 2.3 创建一个从 "tag 名称" 到 "kp_id" 的映射字典，方便快速查找
    #   这将比循环查找快得多
    #   例如: {'binary search': 'P1', 'brute force': 'P2', ...}
    tag_to_kpid_map = pd.Series(df_result.kp_id.values, index=df_result.name).to_dict()

    # 3. 生成边 (edges)
    #   这是一个核心步骤，用来处理 problem 和 tags 的一对多关系

    # 3.1 仅保留我们需要的列：每个问题的 ID 和它对应的 tags 字符串
    df_edges_base = df_name_filtered[['subject_id', 'tags']].copy()

    # 3.2 分割 tags 字符串，将其从 'tag1;tag2' 转换成 ['tag1', 'tag2'] 列表
    #   使用 .str.split(';')
    df_edges_base['tags'] = df_edges_base['tags'].str.split(';')

    # 3.3 使用 explode() 方法，将列表中的每个 tag 展开成独立的一行
    #   这是 pandas 处理一对多关系的强大功能
    #   例如，一行 (P1, ['dp', 'sortings']) 会变成两行：
    #   (P1, 'dp')
    #   (P1, 'sortings')
    df_edges_exploded = df_edges_base.explode('tags')

    #   清理一下可能存在的首尾空格
    df_edges_exploded['tags'] = df_edges_exploded['tags'].str.strip()

    # 4. 映射 kp_id 并构建最终的 DataFrame

    # 4.1 使用之前创建的字典 (tag_to_kpid_map) 来映射 object_id
    #   .map() 函数会根据 'tags' 列中的值，从字典中查找对应的 kp_id
    df_edges_exploded['object_id'] = df_edges_exploded['tags'].map(tag_to_kpid_map)

    # 4.2 添加固定的 'relation' 列
    df_edges_exploded['relation'] = '考察'

    # 4.3 筛选并重排我们最终需要的列
    final_df = df_edges_exploded[['subject_id', 'relation', 'object_id']]

    # 4.4 丢弃那些可能因为 tag 不在 result.csv 中而映射失败的行 (object_id 为空)
    final_df.dropna(subset=['object_id'], inplace=True)

    # 5. 保存到 edges.csv 文件
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')

    print(f"\n处理完成！总共生成了 {len(final_df)} 条关系边。")
    print(f"结果已保存到文件: {output_filename}")

except FileNotFoundError as e:
    print(f"错误：找不到必需的文件: {e}。请确保 name.csv, problems.csv, 和 result.csv 都在当前目录下。")
except Exception as e:
    print(f"处理过程中发生未知错误: {e}")