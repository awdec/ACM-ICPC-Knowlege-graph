# test_neo4j_connection.py
"""
Neo4j数据库连接简单测试
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from neo4j_helper import Neo4jHelper

def test_neo4j_connection():
    """测试Neo4j数据库连接"""
    try:
        # 使用默认配置尝试连接
        helper = Neo4jHelper()
        
        # 简单的连接测试查询
        result = helper.run_query("RETURN 1 as test")
        
        if result and len(result) == 1 and result[0].get('test') == 1:
            print("✓ Neo4j连接测试成功！")
            
            # 检查数据库中的节点类型
            node_types = helper.run_query("""
                CALL db.labels() YIELD label
                RETURN label
                ORDER BY label
            """)
            
            print(f"✓ 数据库中的节点类型: {[r['label'] for r in node_types]}")
            
            # 检查关系类型
            rel_types = helper.run_query("""
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN relationshipType
                ORDER BY relationshipType
            """)
            
            print(f"✓ 数据库中的关系类型: {[r['relationshipType'] for r in rel_types]}")
            
            # 统计各类型节点数量
            counts = helper.run_query("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {}) YIELD value
                RETURN label, value.count as count
                ORDER BY count DESC
            """)
            
            if counts:
                print("✓ 节点数量统计:")
                for item in counts:
                    print(f"  {item['label']}: {item['count']}")
            else:
                # 如果没有APOC插件，使用基本查询
                basic_count = helper.run_query("MATCH (n) RETURN count(n) as total")
                if basic_count:
                    print(f"✓ 总节点数: {basic_count[0]['total']}")
        
        helper.close()
        return True
        
    except Exception as e:
        print(f"✗ Neo4j连接失败: {e}")
        print("请确保:")
        print("1. Neo4j服务正在运行 (默认端口: 7687)")
        print("2. 用户名和密码正确 (默认: neo4j/luogu20201208)")
        print("3. 数据库中已导入ACM-ICPC相关数据")
        return False

if __name__ == "__main__":
    test_neo4j_connection()