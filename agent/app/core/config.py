"""
全局配置 —— 从 .env 读密钥，其余常量硬编码在这里
"""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# --- 加载 .env ---
# .env 在 agent 项目根目录，比 config.py 往上两层
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # agent/
load_dotenv(_PROJECT_ROOT / ".env", override=True)  # override=True 确保每次读最新 .env

# --- 密钥 ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")

# --- 路径 ---
DATA_DIR = _PROJECT_ROOT / "data"                    # React 原文
CHROMA_PERSIST_DIR = _PROJECT_ROOT / "chroma_db"     # Chroma 持久化目录

# --- Embedding ---
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn"   # 国内走 .cn（别用 .com）
EMBEDDING_MODEL = "BAAI/bge-m3"                      # HuggingFace 模型 id
EMBEDDING_DIMENSION = 1024                            # bge-m3 输出维度

# 自托管 BGE-M3：本地权重目录（约 2.2GB，统一放 D 盘，避开 C 盘默认缓存）
# 想换位置就设环境变量 BGE_M3_LOCAL_PATH 覆盖
BGE_M3_LOCAL_PATH = Path(os.getenv("BGE_M3_LOCAL_PATH", r"D:\AI\store\models\bge-m3"))

# --- 切块策略 ---
CHUNK_SIZE = 500       # 每个块最多 500 字符
CHUNK_OVERLAP = 50     # 相邻块重叠 50 字符（防断章取义）

# --- 检索 ---
TOP_K = int(os.getenv("TOP_K", "5"))              # 取最相近的 5 块
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.5"))  # 低于此分数视为"没翻到书"，返回空列表
# 关于距离函数（改之前务必读完，否则阈值会静默失效）：
# vectorstore.py 没设 hnsw:space，Chroma 走默认的 l2 space，
# 返回的 distance 是 L2 距离的平方 = 2 - 2*cos（向量已归一化，范围 [0,4]）。
# 所以 cosine_distance_to_similarity 里的 1 - d/2 恰好等于真余弦相似度。
# 一旦有人把 space 改成 cosine，返回会变成 1 - cos，这个公式和上面的阈值会同时失效。
#
# 0.5 的来历：2026-10-28 实测（practice/probe_distance.py）
#   无关 query 余弦上限 0.4717 / 相关 query 余弦下限 0.6940，0.5 落在断层内。
#   余量只有 0.028，终值待 11/3 用 10 条 eval 集重新定。

# --- 日志 ---
# 在这里配一次就全局生效：所有业务模块都会 import config。
# basicConfig 只在 root logger 还没有 handler 时起作用，所以重复 import 不会叠加 handler。
# 级别用 LOG_LEVEL 环境变量控制（DEBUG 能看到逐块丢弃明细，INFO 只看汇总）。
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
