import pandas as pd

# --- 配置 ---
# 输入文件名
input_filename = 'codeforces_problems_with_solved.csv'
# 输出文件名
output_filename = 'result.csv'
# 要读取的列名
column_to_read = 'tags'
# 标签之间的分隔符 (根据您的示例，这里是分号 ';')
separator = ';'

try:
    df = pd.read_csv(input_filename, usecols=[column_to_read])

    all_tags = df[column_to_read].dropna().str.split(separator).explode()

    unique_tags = all_tags.str.strip().drop_duplicates().reset_index(drop=True)

    result_df = pd.DataFrame({'name': unique_tags})

    result_df.insert(0, 'kp_id', [f'KP{i + 1}' for i in result_df.index])

    result_df.to_csv(output_filename, index=False, encoding='utf-8-sig')

    print(f"处理完成！总共找到 {len(result_df)} 个唯一的标签。")
    print(f"结果已保存到文件: {output_filename}")

except FileNotFoundError:
    print(f"错误：找不到文件 '{input_filename}'。请确保文件存在于当前目录下。")
except KeyError:
    print(f"错误：在 '{input_filename}' 文件中找不到名为 '{column_to_read}' 的列。请检查列标题是否正确。")
except Exception as e:
    print(f"处理过程中发生未知错误: {e}")
