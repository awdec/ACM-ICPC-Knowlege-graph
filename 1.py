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

universities = [
    "beijingdaxue",
    "qinghuadaxue",
    "renmindaxue",
    "beijingjiaotongdaxue",
    "beijingligongdaxue",
    "beihangdaxue",
    "beijingyoufangdaxue",
    "shanghaidaxue",
    "fudandaxue",
    "tongjidaxue",
    "shanghaijiaotongdaxue",
    "dongnanidaxue",
    "nanjingdaxue",
    "hehaidaxue",
    "southeastdaxue",
    "zhejiangdaxue",
    "hangzhoudianzi",
    "huazhongkejidaxue",
    "wuhandaxue",
    "zhongnanshifandaxue",
    "huananligongdaxue",
    "zhongshandaxue",
    "shenzhendaxue",
    "sichuandaxue",
    "xidandaxue",
    "xibeidaxue",
    "xibeiligongdaxue",
    "xianjiaotongdaxue",
    "lanzhoudaxue",
    "zhongkeda"
]

import random


def generate_acm_paragraph(n=5):
    """
    随机生成与 ACM ICPC 解题相关的英文句子，主语固定为 problem。
    n: 句子数量
    return: 拼接好的段落字符串
    """
    subjects = ["The problem", "This problem", "That problem", "Each problem"]
    verbs = [
        "requires", "tests", "focuses on", "is related to",
        "challenges", "involves", "is based on", "covers"
    ]
    objects = [
        "dynamic programming", "graph theory", "a greedy algorithm",
        "data structures", "time complexity analysis", "edge case handling",
        "mathematical proofs", "input and output formatting"
    ]
    adverbs = [
        "heavily", "carefully", "in depth", "under strict limits",
        "for optimization", "step by step", "with precision", "within seconds"
    ]

    def random_sentence():
        subject = random.choice(subjects)
        verb = random.choice(verbs)
        obj = random.choice(objects)
        adv = random.choice(adverbs)

        patterns = [
            f"{subject} {verb} {obj} {adv}.",
            f"{subject} {adv} {verb} {obj}.",
            f"{subject} {verb} {obj}.",
        ]
        return random.choice(patterns)

    return " ".join(random_sentence() for _ in range(n))


# 示例调用
# if __name__ == "__main__":
#     print(generate_acm_paragraph(6))  # 生成 6 句话组成的一段话


def add_list_to_csv(csv_path, column_name, encoding="utf-8"):
    df = pd.read_csv(csv_path, encoding=encoding)
    length = df.iloc[:, 0].dropna().shape[0]
    new_list = []
    for i in range(length):
        # s = str(random.randint(2000, 2020)) + cities[random.randint(0, 9)]
        # s = universities[random.randint(0, 29)] + str(random.randint(1, 10))
        # s = 'uid' + str(random.randint(10000, 10025))
        new_list.append(generate_acm_paragraph())

    df[column_name] = new_list

    df.to_csv(csv_path, index=False, encoding=encoding)


if __name__ == "__main__":
    add_list_to_csv("solution.csv", "content", encoding="gbk")  # 尝试 gbk
