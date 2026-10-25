"""
全局配置 —— 从 .env 读密钥，其余常量硬编码在这里
"""
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
TOP_K = 5              # 取最相近的 5 块
SCORE_THRESHOLD = 0.3  # 低于此分数视为"没翻到书"，返回空列表
# 注意：Chroma 默认用余弦距离（0=完全相同，2=完全相反）
# 转成相似度 = 1 - 距离/2，所以阈值 0.3 大致对应距离 1.4 以内
