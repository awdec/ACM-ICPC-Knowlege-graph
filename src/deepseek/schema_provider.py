# src/deepseek/schema_provider.py
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from neo4j_helper import Neo4jHelper
from config.config_manager import ConfigManager

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class NodeType:
    """节点类型信息"""
    label: str
    properties: List[Dict[str, str]]  # [{"property": "name", "type": "String"}]
    approximate_count: int = 0


@dataclass
class RelationshipType:
    """关系类型信息"""
    type_name: str
    start_node_labels: List[str]
    end_node_labels: List[str]
    properties: List[Dict[str, str]]


@dataclass
class GraphSchema:
    """图数据库 Schema"""
    node_types: List[NodeType]
    relationship_types: List[RelationshipType]
    constraints: List[str]
    indexes: List[str]
    
    def to_text(self) -> str:
        """转换为文本格式，供 LLM 理解"""
        text_parts = ["图数据库Schema信息：\n"]
        
        # 节点类型
        text_parts.append("【节点类型】")
        for i, node in enumerate(self.node_types, 1):
            count_info = f"，约{node.approximate_count}个" if node.approximate_count > 0 else ""
            text_parts.append(f"{i}. {node.label} (节点{count_info})")
            
            for prop in node.properties:
                prop_name = prop.get("property", "")
                prop_type = prop.get("type", "String")
                text_parts.append(f"   - {prop_name}: {prop_type}")
        
        # 关系类型
        text_parts.append("\n【关系类型】")
        for i, rel in enumerate(self.relationship_types, 1):
            start_labels = ", ".join(rel.start_node_labels) if rel.start_node_labels else "Any"
            end_labels = ", ".join(rel.end_node_labels) if rel.end_node_labels else "Any"
            text_parts.append(f"{i}. {rel.type_name}: {start_labels} -> {end_labels}")
            
            if rel.properties:
                for prop in rel.properties:
                    prop_name = prop.get("property", "")
                    prop_type = prop.get("type", "String")
                    text_parts.append(f"   - {prop_name}: {prop_type}")
        
        return "\n".join(text_parts)


class SchemaProvider:
    """Schema 提供者"""
    
    _instance: Optional['SchemaProvider'] = None
    _schema: Optional[GraphSchema] = None
    
    def __new__(cls, neo4j_helper: Optional[Neo4jHelper] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, neo4j_helper: Optional[Neo4jHelper] = None):
        """初始化 Schema 提供者
        
        Args:
            neo4j_helper: Neo4j 连接器，如果为 None 则创建新实例
        """
        if not hasattr(self, '_initialized'):
            self.neo4j_helper = neo4j_helper
            if self.neo4j_helper is None:
                config = ConfigManager().get_neo4j_config()
                self.neo4j_helper = Neo4jHelper(
                    uri=config.uri,
                    user=config.user,
                    pwd=config.password
                )
            self._initialized = True
    
    def get_schema(self, force_refresh: bool = False) -> GraphSchema:
        """获取图数据库 Schema
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            GraphSchema 对象
        """
        if self._schema is None or force_refresh:
            logger.info("Loading graph schema from Neo4j...")
            self._schema = self._load_schema()
            logger.info("Graph schema loaded successfully")
        
        return self._schema
    
    def _load_schema(self) -> GraphSchema:
        """从 Neo4j 加载 Schema"""
        try:
            # 获取节点类型和属性
            node_types = self._get_node_types()
            
            # 获取关系类型和属性
            relationship_types = self._get_relationship_types()
            
            # 获取约束信息
            constraints = self._get_constraints()
            
            # 获取索引信息
            indexes = self._get_indexes()
            
            return GraphSchema(
                node_types=node_types,
                relationship_types=relationship_types,
                constraints=constraints,
                indexes=indexes
            )
            
        except Exception as e:
            logger.error(f"Failed to load schema: {str(e)}")
            # 返回默认 Schema
            return self._get_default_schema()
    
    def _get_node_types(self) -> List[NodeType]:
        """获取节点类型信息"""
        node_types = []
        
        try:
            # 尝试使用 APOC 或者基本查询获取节点信息
            # 首先尝试获取所有标签
            label_query = "CALL db.labels() YIELD label RETURN label"
            labels_result = self.neo4j_helper.run_query(label_query)
            
            for record in labels_result:
                label = record["label"]
                
                # 获取该标签的属性信息
                properties = self._get_node_properties(label)
                
                # 获取节点数量（采样）
                count = self._get_node_count(label)
                
                node_types.append(NodeType(
                    label=label,
                    properties=properties,
                    approximate_count=count
                ))
            
        except Exception as e:
            logger.warning(f"Failed to get node types: {str(e)}")
            # 返回已知的默认节点类型
            node_types = self._get_default_node_types()
        
        return node_types
    
    def _get_node_properties(self, label: str) -> List[Dict[str, str]]:
        """获取节点的属性信息"""
        try:
            # 查询该标签的一个示例节点来获取属性
            query = f"MATCH (n:{label}) RETURN keys(n) AS props LIMIT 1"
            result = self.neo4j_helper.run_query(query)
            
            if result:
                props = result[0]["props"]
                return [{"property": prop, "type": "String"} for prop in props]
            
        except Exception as e:
            logger.debug(f"Failed to get properties for {label}: {str(e)}")
        
        return []
    
    def _get_node_count(self, label: str) -> int:
        """获取节点数量"""
        try:
            query = f"MATCH (n:{label}) RETURN count(n) AS count"
            result = self.neo4j_helper.run_query(query)
            if result:
                return result[0]["count"]
        except Exception as e:
            logger.debug(f"Failed to get count for {label}: {str(e)}")
        
        return 0
    
    def _get_relationship_types(self) -> List[RelationshipType]:
        """获取关系类型信息"""
        relationship_types = []
        
        try:
            # 获取所有关系类型
            rel_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            rel_result = self.neo4j_helper.run_query(rel_query)
            
            for record in rel_result:
                rel_type = record["relationshipType"]
                
                # 获取关系的起始和结束节点标签
                start_labels, end_labels = self._get_relationship_node_labels(rel_type)
                
                # 获取关系属性
                properties = self._get_relationship_properties(rel_type)
                
                relationship_types.append(RelationshipType(
                    type_name=rel_type,
                    start_node_labels=start_labels,
                    end_node_labels=end_labels,
                    properties=properties
                ))
            
        except Exception as e:
            logger.warning(f"Failed to get relationship types: {str(e)}")
            relationship_types = self._get_default_relationship_types()
        
        return relationship_types
    
    def _get_relationship_node_labels(self, rel_type: str) -> tuple:
        """获取关系的起始和结束节点标签"""
        try:
            query = f"""
            MATCH (a)-[r:`{rel_type}`]->(b)
            RETURN DISTINCT labels(a) AS start_labels, labels(b) AS end_labels
            LIMIT 10
            """
            result = self.neo4j_helper.run_query(query)
            
            start_labels = set()
            end_labels = set()
            
            for record in result:
                start_labels.update(record["start_labels"])
                end_labels.update(record["end_labels"])
            
            return list(start_labels), list(end_labels)
            
        except Exception as e:
            logger.debug(f"Failed to get node labels for {rel_type}: {str(e)}")
            return [], []
    
    def _get_relationship_properties(self, rel_type: str) -> List[Dict[str, str]]:
        """获取关系的属性信息"""
        try:
            query = f"MATCH ()-[r:`{rel_type}`]->() RETURN keys(r) AS props LIMIT 1"
            result = self.neo4j_helper.run_query(query)
            
            if result:
                props = result[0]["props"]
                return [{"property": prop, "type": "String"} for prop in props]
            
        except Exception as e:
            logger.debug(f"Failed to get properties for {rel_type}: {str(e)}")
        
        return []
    
    def _get_constraints(self) -> List[str]:
        """获取约束信息"""
        try:
            query = "CALL db.constraints() YIELD description RETURN description"
            result = self.neo4j_helper.run_query(query)
            return [record["description"] for record in result]
        except Exception:
            return []
    
    def _get_indexes(self) -> List[str]:
        """获取索引信息"""
        try:
            query = "CALL db.indexes() YIELD description RETURN description"
            result = self.neo4j_helper.run_query(query)
            return [record["description"] for record in result]
        except Exception:
            return []
    
    def _get_default_schema(self) -> GraphSchema:
        """获取默认 Schema（基于已知的 ACM-ICPC 数据结构）"""
        return GraphSchema(
            node_types=self._get_default_node_types(),
            relationship_types=self._get_default_relationship_types(),
            constraints=[],
            indexes=[]
        )
    
    def _get_default_node_types(self) -> List[NodeType]:
        """获取默认节点类型"""
        return [
            NodeType(
                label="Problem",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "name", "type": "String"},
                    {"property": "rating", "type": "Integer"},
                    {"property": "source", "type": "String"}
                ],
                approximate_count=2000
            ),
            NodeType(
                label="Tag",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "name", "type": "String"}
                ],
                approximate_count=150
            ),
            NodeType(
                label="Contest",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "name", "type": "String"}
                ],
                approximate_count=50
            ),
            NodeType(
                label="Team",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "name", "type": "String"}
                ],
                approximate_count=300
            ),
            NodeType(
                label="Person",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "name", "type": "String"}
                ],
                approximate_count=500
            ),
            NodeType(
                label="Solution",
                properties=[
                    {"property": "id", "type": "String"},
                    {"property": "writer", "type": "String"},
                    {"property": "content", "type": "String"}
                ],
                approximate_count=800
            )
        ]
    
    def _get_default_relationship_types(self) -> List[RelationshipType]:
        """获取默认关系类型"""
        return [
            RelationshipType(
                type_name="HAS_TAG",
                start_node_labels=["Problem"],
                end_node_labels=["Tag"],
                properties=[]
            ),
            RelationshipType(
                type_name="HAS_SOLUTION",
                start_node_labels=["Problem"],
                end_node_labels=["Solution"],
                properties=[]
            ),
            RelationshipType(
                type_name="AUTHOR",
                start_node_labels=["Solution"],
                end_node_labels=["Person"],
                properties=[]
            ),
            RelationshipType(
                type_name="PARTICIPATED_IN",
                start_node_labels=["Team"],
                end_node_labels=["Contest"],
                properties=[]
            ),
            RelationshipType(
                type_name="PLACED",
                start_node_labels=["Team"],
                end_node_labels=["Contest"],
                properties=[
                    {"property": "rank", "type": "String"},
                    {"property": "region", "type": "String"}
                ]
            )
        ]
    
    def get_schema_text(self) -> str:
        """获取 Schema 的文本描述"""
        schema = self.get_schema()
        return schema.to_text()
    
    def refresh_schema(self) -> None:
        """刷新 Schema 缓存"""
        logger.info("Refreshing schema cache...")
        self._schema = None
        self.get_schema(force_refresh=True)