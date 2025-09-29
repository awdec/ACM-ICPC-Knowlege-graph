import os
import random
import pandas as pd

cities = [
    "beijing",
    "shanghai",
    "guangzhou",
    "shenzhen",
    "chengdu",
    "chongqing",
    "wuhan",
    "nanjing",
    "xian",
    "hangzhou"
]


def robust_read_csv(path, encodings=("utf-8", "utf-8-sig", "gbk", "latin1"),
                    seps=(",", "\t", ";", "|")):
    """
    尝试多种 encoding 和 sep 读取 CSV。
    返回 (df, used_encoding, used_sep, was_empty_file)
    如果文件不存在 -> FileNotFoundError
    如果文件为空 -> returns (None, None, None, True)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    if os.path.getsize(path) == 0:
        # 文件存在但为空
        return None, None, None, True

    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, engine="python")
                if df.shape[1] == 0:
                    # 没有解析出列，继续尝试
                    continue
                return df, enc, sep, False
            except Exception as e:
                last_err = e
                continue

    raise ValueError(
        f"无法解析文件 {path}。尝试 encodings={encodings} seps={seps}。最后错误：{last_err}"
    )


def add_list_to_csv(csv_path, column_name="name", encoding="utf-8", n_rows_when_empty=1000):
    """
    - 如果文件为空：创建一个有 n_rows_when_empty 行的表格，并把生成的 list 放到第一列或指定列。
    - 如果文件存在且可读：长度用文件行数（len(df)），生成相同长度的 list。
    - 如果第一列全是空或列名为空（""），把 list 写入第一列；否则写入 column_name（不存在则创建）。
    """

    try:
        df, used_enc, used_sep, was_empty = robust_read_csv(csv_path)
    except FileNotFoundError:
        was_empty = True
        df = None
        used_enc = encoding
        used_sep = ","
    except Exception as e:
        raise

    if was_empty:

        df = pd.DataFrame(index=range(n_rows_when_empty))
        row_count = n_rows_when_empty
        used_enc = encoding  # 用用户提供的 encoding 保存
        print(f"文件为空或不存在，将创建一个 {n_rows_when_empty} 行的表格并写入新列。")
    else:
        row_count = len(df)
        print(f"已读取 CSV，行数={row_count}，使用 encoding={used_enc} sep={used_sep}")

    new_list = []

    for _ in range(row_count):
        new_list.append('S' + str(_+1))

    if df.shape[1] == 0:
        df[column_name] = new_list
        print(f"原 CSV 没有任何列，已创建列 '{column_name}' 并写入数据。")
    else:
        first_col_name = df.columns[0]
        first_col_all_null = df[first_col_name].isnull().all() or all(
            str(x).strip() == "" for x in df[first_col_name].fillna(""))
        if first_col_all_null or str(first_col_name).strip() == "":
            if str(first_col_name).strip() == "":
                # 重命名空列名为 column_name
                df.rename(columns={first_col_name: column_name}, inplace=True)
                df[column_name] = new_list
                print(f"第一列列名为空，已将其命名为 '{column_name}' 并写入数据。")
            else:
                df[first_col_name] = new_list
                print(f"第一列（'{first_col_name}'）全为空，已在该列写入数据。")
        else:
            df[column_name] = new_list
            print(f"第一列不为空，已在列 '{column_name}' 写入/覆盖数据。")

    df.to_csv(csv_path, index=False, encoding=used_enc)
    print(f"保存完成：{csv_path}（encoding={used_enc}） 行数={len(df)}")


if __name__ == "__main__":
    add_list_to_csv("solution.csv", column_name="id", encoding="gbk", n_rows_when_empty=1000)
