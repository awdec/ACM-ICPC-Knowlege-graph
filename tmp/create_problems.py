import pandas as pd

# --- 配置 ---
# 输入文件名
input_filename = 'codeforces_problems_with_solved.csv'
# 输出文件名
output_filename = 'problems.csv'


# 定义一个函数，用于根据 rating 映射难度等级
def map_rating_to_difficulty(rating):
    """根据 rating 值返回难度字符串"""
    if rating <= 1200:
        return 'Easy'
    elif rating <= 1900:
        return 'Mid'
    elif rating <= 2400:
        return 'Hard'
    else:  # rating > 2400
        return 'Very Hard'


try:
    # 1. 读取 name.csv 文件
    # 加载所有需要的列
    df = pd.read_csv(input_filename)
    print(f"成功读取 '{input_filename}'，共 {len(df)} 行数据。")

    # 2. 数据清洗与筛选
    # 2.1 忽略 rating 为空的行
    # 使用 dropna() 方法，subset 参数指定只检查 'rating' 列是否为空
    df_filtered = df.dropna(subset=['rating']).copy()

    # 2.2 确保 rating 列是数值类型 (例如整数)，以便进行比较
    df_filtered['rating'] = pd.to_numeric(df_filtered['rating'], errors='coerce').astype('int')
    print(f"筛选掉 rating 为空的行后，剩余 {len(df_filtered)} 行有效数据。")

    # 3. 创建新的 DataFrame 用于存储结果
    # 创建一个空的 DataFrame，后续逐列填充
    result_df = pd.DataFrame()

    # 4. 根据规则生成新的列
    # 4.1 'title' 列：直接使用 name.csv 的 'name' 列
    # 使用 .reset_index(drop=True) 来确保索引是连续的，这对于后续赋值很重要
    result_df['title'] = df_filtered['name'].reset_index(drop=True)

    # 4.2 'difficulty' 列：应用我们定义的函数
    # 使用 .apply() 方法将函数作用于 'rating' 列的每一个值
    result_df['difficulty'] = df_filtered['rating'].apply(map_rating_to_difficulty).reset_index(drop=True)

    # 4.3 'source' 列：拼接 contestId 和 index
    # 首先确保这两列是字符串类型，然后进行拼接
    base_url = 'https://codeforces.com/problemset/problem/'
    contest_ids = df_filtered['contestId'].astype(str)
    indices = df_filtered['index'].astype(str)
    result_df['source'] = (base_url + contest_ids + '/' + indices).reset_index(drop=True)

    # 4.4 'id' 列：从 P1 开始依次编号
    # 使用 f-string 和 result_df 的新索引来生成
    result_df.insert(0, 'id', [f'P{i + 1}' for i in result_df.index])

    # 5. 保存到 problems.csv 文件
    # 设置 index=False เพื่อไม่ให้ pandas 将索引写入文件
    # 使用 encoding='utf-8-sig' 确保在 Excel 中打开中文不会乱码
    result_df.to_csv(output_filename, index=False, encoding='utf-8-sig')

    print(f"\n处理完成！")
    print(f"结果已保存到文件: {output_filename}")

except FileNotFoundError:
    print(f"错误：找不到文件 '{input_filename}'。请确保文件存在于当前目录下。")
except KeyError as e:
    print(
        f"错误：在 '{input_filename}' 文件中找不到必需的列: {e}。请检查文件是否包含 contestId, index, name, rating 等列。")
except Exception as e:
    print(f"处理过程中发生未知错误: {e}")