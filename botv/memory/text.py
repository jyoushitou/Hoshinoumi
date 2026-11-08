# ===================== 分词工具（v8） =====================
# 单独成文件，避免 context 和 retrieval 互相 import 形成环。

import jieba

# 停用词：单字和语气词，做关键词没意义
STOPWORDS = {"的", "了", "是", "我", "你", "在", "有", "就", "不", "都",
             "吗", "吧", "啊", "哦", "呀", "呢", "呗", "啦"}


def extract_keywords(text):
    """jieba 分词 + 过滤停用词与单字"""
    return [w for w in jieba.lcut(text or "") if len(w) > 1 and w not in STOPWORDS]
