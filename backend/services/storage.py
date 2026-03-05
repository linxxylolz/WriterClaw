import json
import os
from typing import List, Dict, Any
from datetime import datetime

DATA_FILE = "papers_data.json"

def load_papers() -> Dict[str, Any]:
    """从JSON文件加载文稿数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_papers(papers_db: Dict[str, Any]) -> None:
    """保存文稿数据到JSON文件"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(papers_db, f, ensure_ascii=False, indent=2)

def initialize_storage() -> Dict[str, Any]:
    """初始化存储，加载已有数据"""
    return load_papers()

def backup_paper(paper_data: Dict[str, Any], backup_dir: str = "backups") -> str:
    """备份单篇文稿数据"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    paper_id = paper_data.get('id', '')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"{paper_id}_{timestamp}.json")
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(paper_data, f, ensure_ascii=False, indent=2)
    
    return backup_file

def get_paper_history(paper_id: str, backup_dir: str = "backups") -> List[Dict[str, Any]]:
    """获取文稿的历史版本"""
    history = []
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.startswith(paper_id) and filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        history.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    continue
    
    history.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return history

def cleanup_old_backups(backup_dir: str = "backups", keep_count: int = 10):
    """清理过旧的备份文件，每个文稿保留最近的keep_count个版本"""
    if not os.path.exists(backup_dir):
        return
    
    paper_backups = {}
    for filename in os.listdir(backup_dir):
        if filename.endswith('.json'):
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                paper_id = parts[0]
                if paper_id not in paper_backups:
                    paper_backups[paper_id] = []
                paper_backups[paper_id].append(filename)
    
    for paper_id, files in paper_backups.items():
        if len(files) > keep_count:
            files.sort(reverse=True)
            for filename in files[keep_count:]:
                filepath = os.path.join(backup_dir, filename)
                try:
                    os.remove(filepath)
                except OSError:
                    pass
