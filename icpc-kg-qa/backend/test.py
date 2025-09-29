from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"   # 或 "bolt://localhost:7687"；云服务通常用 neo4j+s://...
AUTH = ("neo4j", "luogu20201208")

driver = GraphDatabase.driver(URI, auth=AUTH)

try:
    # 立刻验证连接（可选，但推荐）
    driver.verify_connectivity()

    # 打开 session（指定 database 名称，例如 "neo4j"）
    with driver.session(database="neo4j") as session:
        # 读：auto-commit 事务
        result = session.run("MATCH (n) RETURN n LIMIT 5")
        for record in result:
            print(record)

        # 写：用 execute_write 更安全（会自动重试）
        def create_person(tx, name):
            tx.run("MERGE (p:Person {name: $name})", name=name)

        session.execute_write(create_person, "Alice")

finally:
    driver.close()
