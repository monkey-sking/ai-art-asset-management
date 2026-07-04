#!/usr/bin/env python3
"""初始化 SQLite 数据库并插入测试数据"""
import os
import sys

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from storage.database.shared.model import (
    Base, Project, Node, AssetRequest, ImageAsset,
    PromptTemplate, GenerationTask, ExportPreset, ExportBatch
)

# SQLite 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'local_dev.db')
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

def init_database():
    """创建表并插入测试数据"""
    engine = create_engine(DB_URL, echo=False)
    
    # 创建所有表
    print("创建数据表...")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 检查是否已有数据
    if session.query(Project).count() > 0:
        print("数据库已初始化，跳过插入测试数据")
        session.close()
        return
    
    print("插入测试数据...")
    
    # 1. 创建项目
    project = Project(name="测试游戏项目", description="AI美术资产生产管理测试项目")
    session.add(project)
    session.flush()
    print(f"  ✓ 项目: {project.name} (ID: {project.id})")
    
    # 2. 创建节点树
    nodes_data = [
        {"name": "道具", "children": ["普通道具", "稀有道具"]},
        {"name": "技能", "children": ["普通技能", "高级技能"]},
        {"name": "装备", "children": ["普通装备", "稀有装备"]},
    ]
    
    nodes = {}
    for item in nodes_data:
        parent = Node(project_id=project.id, name=item["name"], node_type="category", sort_order=len(nodes))
        session.add(parent)
        session.flush()
        nodes[item["name"]] = parent
        print(f"  ✓ 节点: {item['name']} (ID: {parent.id})")
        
        for child_name in item["children"]:
            child = Node(project_id=project.id, parent_id=parent.id, name=child_name, node_type="category", sort_order=len(nodes))
            session.add(child)
            session.flush()
            nodes[child_name] = child
            print(f"    ✓ 子节点: {child_name} (ID: {child.id})")
    
    # 3. 创建提示词模板
    templates = [
        PromptTemplate(
            name="道具图标模板",
            positive_prompt="游戏图标，{{asset_name}}，{{asset_type}}，高质量，清晰边缘，适合手机屏幕，矢量风格",
            negative_prompt="模糊，低质量，复杂背景，照片风格",
            variables={"asset_name": "资产名称", "asset_type": "资产类型"}
        ),
        PromptTemplate(
            name="技能图标模板",
            positive_prompt="游戏技能图标，{{asset_name}}，魔法特效，炫酷光效，游戏美术风格",
            negative_prompt="模糊，低质量，真实照片",
            variables={"asset_name": "技能名称"}
        ),
        PromptTemplate(
            name="装备图标模板",
            positive_prompt="游戏装备图标，{{asset_name}}，金属质感，精细纹理，游戏美术风格",
            negative_prompt="模糊，低质量，卡通风格",
            variables={"asset_name": "装备名称"}
        ),
    ]
    for t in templates:
        session.add(t)
    session.flush()
    print(f"  ✓ 提示词模板: {len(templates)} 个")
    
    # 4. 创建导出预设
    presets = [
        ExportPreset(name="手机图标预设", final_width=256, final_height=256, padding=16, remove_background=True),
        ExportPreset(name="PC图标预设", final_width=512, final_height=512, padding=32, remove_background=True),
    ]
    for p in presets:
        session.add(p)
    session.flush()
    print(f"  ✓ 导出预设: {len(presets)} 个")
    
    # 5. 创建资产需求
    assets_data = [
        {"name": "生命药水", "type": "道具", "rarity": "普通", "status": "已定稿", "node": "普通道具", "desc": "红色瓶装药水，散发柔和光芒"},
        {"name": "魔法药水", "type": "道具", "rarity": "普通", "status": "已定稿", "node": "普通道具", "desc": "蓝色瓶装药水，流动魔力效果"},
        {"name": "稀有宝石", "type": "道具", "rarity": "稀有", "status": "已定稿", "node": "稀有道具", "desc": "闪耀的六角形宝石"},
        {"name": "火球术", "type": "技能", "rarity": "普通", "status": "待生成", "node": "普通技能", "desc": "燃烧的火焰球体"},
        {"name": "冰霜箭", "type": "技能", "rarity": "普通", "status": "生成中", "node": "普通技能", "desc": "寒冰附魔的箭矢"},
        {"name": "雷霆一击", "type": "技能", "rarity": "高级", "status": "待筛选", "node": "高级技能", "desc": "闪电环绕的攻击特效"},
        {"name": "铁剑", "type": "装备", "rarity": "普通", "status": "已导出", "node": "普通装备", "desc": "基础款铁制长剑"},
        {"name": "魔法杖", "type": "装备", "rarity": "稀有", "status": "已导出", "node": "稀有装备", "desc": "镶嵌宝石的法杖"},
    ]
    
    for item in assets_data:
        asset = AssetRequest(
            node_id=nodes[item["node"]].id,
            name=item["name"],
            asset_type=item["type"],
            description=item["desc"],
            status=item["status"],
            priority=item["rarity"],
        )
        session.add(asset)
    session.flush()
    print(f"  ✓ 资产需求: {len(assets_data)} 个")
    
    session.commit()
    session.close()
    print("\n✅ 数据库初始化完成！")
    print(f"   数据库路径: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    init_database()
